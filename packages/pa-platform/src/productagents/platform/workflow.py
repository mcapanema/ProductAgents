"""WorkflowService — persisted, editable workflow definitions (Plan 2).

Workflows are DB-backed definitions now, not code entry points. This service is
the single Application-Layer face for both editing (CRUD + validate + palette)
and running: ``run`` loads a definition and hands it to a DecisionService.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from productagents.core.models import WorkflowDefinition
from productagents.platform import events as ev
from productagents.platform.context import open_workflow_store
from productagents.platform.session import Session

logger = logging.getLogger(__name__)

_L = list  # ponytail: 'list' method shadows the builtin under ty; alias keeps it honest


def _summary(defn: WorkflowDefinition, *, is_default: bool) -> dict:
    return {
        "name": defn.name,
        "title": defn.title,
        "description": defn.description,
        "is_default": is_default,
    }


class WorkflowService:
    def __init__(
        self,
        decision_service,
        *,
        workspace: str,
        store_opener,
        human_in_the_loop: bool = False,
    ) -> None:
        self._decisions = decision_service
        self._workspace = workspace
        self._open = store_opener
        self._hitl = human_in_the_loop

    @classmethod
    def create(
        cls,
        model,
        *,
        recorder=None,
        human_in_the_loop: bool = False,
        persist_events: bool = True,
        workspace: str = "default",
        store_opener=open_workflow_store,
    ) -> WorkflowService:
        from productagents.platform.decision_service import DecisionService

        decisions = DecisionService.for_model(
            model,
            recorder=recorder,
            human_in_the_loop=human_in_the_loop,
            persist_events=persist_events,
            workspace=workspace,
        )
        return cls(
            decisions,
            workspace=workspace,
            store_opener=store_opener,
            human_in_the_loop=human_in_the_loop,
        )

    def _store(self):
        return self._open(workspace=self._workspace)

    async def _seed(self, store) -> None:
        from productagents.agents.default_workflow import default_definition

        await store.ensure_default(default_definition())

    async def list(self) -> _L[dict]:
        async with self._store() as store:
            await self._seed(store)
            defns = await store.list()
            default = await store.get_default()
            default_name = default.name if default else None
            return [_summary(d, is_default=d.name == default_name) for d in defns]

    async def get(self, name: str) -> WorkflowDefinition | None:
        async with self._store() as store:
            await self._seed(store)
            return await store.get(name)

    async def show(self, name: str) -> dict | None:
        from productagents.agents.topology import definition_topology

        async with self._store() as store:
            await self._seed(store)
            defn = await store.get(name)
            if defn is None:
                return None
            default = await store.get_default()
            detail = _summary(defn, is_default=bool(default and default.name == name))
            detail["definition"] = defn.model_dump(mode="json")
            detail["topology"] = definition_topology(defn, human_in_the_loop=self._hitl)
            return detail

    async def create_workflow(
        self, name: str, title: str, description: str = ""
    ) -> dict:
        _validate_name(name)
        defn = WorkflowDefinition(name=name, title=title, description=description)
        async with self._store() as store:
            await self._seed(store)
            if await store.get(name) is not None:
                raise ValueError(f"workflow already exists: {name}")
            await store.save(defn)
        return _summary(defn, is_default=False)

    async def clone(self, source_name: str, new_name: str, *, title=None) -> dict:
        _validate_name(new_name)
        async with self._store() as store:
            await self._seed(store)
            src = await store.get(source_name)
            if src is None:
                raise ValueError(f"no such workflow: {source_name}")
            if await store.get(new_name) is not None:
                raise ValueError(f"workflow already exists: {new_name}")
            clone = src.model_copy(
                update={
                    "name": new_name,
                    "title": title or f"{src.title} (copy)",
                    "builtin": False,
                }
            )
            await store.save(clone, is_default=False)
        return _summary(clone, is_default=False)

    async def save(self, defn_dict: dict) -> dict:
        from productagents.agents.workflow_validation import validate_definition

        defn = WorkflowDefinition.model_validate(defn_dict)
        errors = validate_definition(defn)
        if errors:
            raise ValueError("; ".join(errors))
        async with self._store() as store:
            await self._seed(store)
            existing = await store.get(defn.name)
            if existing is not None and existing.builtin:
                # A client can't strip the undeletable-builtin flag by omitting
                # it from the payload — the store writes `builtin` verbatim on
                # every save, so this is the one place that guards it.
                defn = defn.model_copy(update={"builtin": True})
            await store.save(defn)
            default = await store.get_default()
        return _summary(defn, is_default=bool(default and default.name == defn.name))

    async def rename(self, name: str, new_name: str) -> dict:
        _validate_name(new_name)
        async with self._store() as store:
            await self._seed(store)
            defn = await store.get(name)
            if defn is None:
                raise ValueError(f"no such workflow: {name}")
            if defn.builtin:
                raise ValueError(f"cannot rename built-in workflow: {name}")
            if await store.get(new_name) is not None:
                raise ValueError(f"workflow already exists: {new_name}")
            was_default = await store.get_default()
            renamed = defn.model_copy(update={"name": new_name})
            await store.save(
                renamed,
                is_default=bool(was_default and was_default.name == name),
            )
            await store.delete(name)
        return _summary(
            renamed, is_default=bool(was_default and was_default.name == name)
        )

    async def delete(self, name: str) -> None:
        async with self._store() as store:
            await self._seed(store)
            await store.delete(name)

    async def set_default(self, name: str) -> None:
        async with self._store() as store:
            await self._seed(store)
            await store.set_default(name)

    async def validate(self, defn_dict: dict) -> _L[str]:
        from productagents.agents.workflow_validation import validate_definition

        return validate_definition(WorkflowDefinition.model_validate(defn_dict))

    def palette(self) -> _L[dict]:
        from productagents.agents.node_kinds import KIND_REGISTRY, PLACEABLE

        out = []
        for kind_id in PLACEABLE:
            k = KIND_REGISTRY[kind_id]
            out.append(
                {
                    "kind": k.kind,
                    "label": k.label,
                    "role": k.role,
                    "singleton": k.singleton,
                    "prompts": list(k.prompts),
                    "reads": sorted(k.reads),
                    "writes": sorted(k.writes),
                }
            )
        return out

    async def run(
        self, name: str, initiative, evidence_spec: str, *, approver=None
    ) -> tuple[Session, AsyncIterator[ev.Event]]:
        defn = await self.get(name)
        if defn is None:
            raise KeyError(f"unknown workflow: {name!r}")
        return self._decisions.start_session(
            initiative, evidence_spec, approver=approver, definition=defn
        )

    def cancel(self, session_id: str) -> bool:
        return self._decisions.cancel(session_id)


def _validate_name(name: str) -> None:
    if not name or not name.strip():
        raise ValueError("workflow name must not be empty")
    if any(c.isspace() for c in name):
        raise ValueError("workflow name must not contain whitespace")
