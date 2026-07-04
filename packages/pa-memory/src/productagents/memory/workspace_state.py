"""Workspace-state stores: configuration, connector config, and preferences.

Like ``EventStore``, the ``AsyncSession`` is injected by the platform boundary —
this module builds no engine. Rows are primitive KV/JSON; the *meaning* of keys
(whitelists, env-var mapping, precedence) lives a layer above in
``platform.configuration``, keeping pa-memory below pa-platform in the DAG.
Secret values must never be written here — connector blocks reference secrets
as ``<field>_env`` names only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from productagents.core.models import WorkflowDefinition
from productagents.memory.tables import (
    ConnectorConfigRow,
    DecisionRow,
    OutcomeRow,
    PreferenceRow,
    RuntimeSessionRow,
    WorkflowDefinitionRow,
    WorkspaceConfigRow,
    WorkspaceRow,
)

_L = list  # ponytail: 'list' method shadows the builtin under ty; alias keeps it honest


def _now() -> str:
    return datetime.now(UTC).isoformat()


class WorkspaceConfigStore:
    """Workspace configuration values (friendly key -> env-shaped string)."""

    def __init__(self, session: AsyncSession, workspace: str = "default") -> None:
        self._session = session
        self._workspace = workspace

    async def all(self) -> dict[str, str]:
        rows = (
            await self._session.execute(
                select(WorkspaceConfigRow).where(
                    WorkspaceConfigRow.workspace == self._workspace
                )
            )
        ).scalars()
        return {row.key: row.value for row in rows}

    async def set(self, key: str, value: str) -> None:
        await self._session.merge(
            WorkspaceConfigRow(
                workspace=self._workspace, key=key, value=value, updated_at=_now()
            )
        )
        await self._session.commit()

    async def delete(self, key: str) -> None:
        await self._session.execute(
            delete(WorkspaceConfigRow).where(
                WorkspaceConfigRow.workspace == self._workspace,
                WorkspaceConfigRow.key == key,
            )
        )
        await self._session.commit()


class ConnectorConfigStore:
    """Raw connector config blocks (registry key -> dict, YAML-block shaped)."""

    def __init__(self, session: AsyncSession, workspace: str = "default") -> None:
        self._session = session
        self._workspace = workspace

    async def all(self) -> dict[str, dict]:
        rows = (
            await self._session.execute(
                select(ConnectorConfigRow).where(
                    ConnectorConfigRow.workspace == self._workspace
                )
            )
        ).scalars()
        return {row.connector: row.config for row in rows}

    async def set(self, connector: str, config: dict) -> None:
        await self._session.merge(
            ConnectorConfigRow(
                workspace=self._workspace,
                connector=connector,
                config=config,
                updated_at=_now(),
            )
        )
        await self._session.commit()


class PreferenceStore:
    """User-experience preferences (key -> string). Never affects execution."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def all(self) -> dict[str, str]:
        rows = (await self._session.execute(select(PreferenceRow))).scalars()
        return {row.key: row.value for row in rows}

    async def get(self, key: str) -> str | None:
        row = await self._session.get(PreferenceRow, key)
        return row.value if row is not None else None

    async def set(self, key: str, value: str) -> None:
        await self._session.merge(
            PreferenceRow(key=key, value=value, updated_at=_now())
        )
        await self._session.commit()


class WorkspaceRegistry:
    """The workspace registry rows: one per project/team scope."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> _L[dict[str, Any]]:
        rows = (
            await self._session.execute(
                select(WorkspaceRow).order_by(WorkspaceRow.name)
            )
        ).scalars()
        return [{"name": r.name, "created_at": r.created_at} for r in rows]

    async def get(self, name: str) -> dict | None:
        row = await self._session.get(WorkspaceRow, name)
        return {"name": row.name, "created_at": row.created_at} if row else None

    async def create(self, name: str) -> dict:
        if await self._session.get(WorkspaceRow, name) is not None:
            raise ValueError(f"workspace already exists: {name}")
        row = WorkspaceRow(name=name, created_at=_now())
        self._session.add(row)
        await self._session.commit()
        return {"name": row.name, "created_at": row.created_at}

    async def ensure(self, name: str) -> None:
        if await self._session.get(WorkspaceRow, name) is None:
            self._session.add(WorkspaceRow(name=name, created_at=_now()))
            await self._session.commit()


async def rename_workspace(session: AsyncSession, old: str, new: str) -> None:
    """Move every pa-memory row scoped to ``old`` under ``new``.

    No commit — the caller owns the transaction (the platform composes this
    with the pa-knowledge half and commits once, so the DB side of a rename
    is atomic). The registry row swap preserves the original created_at.
    """
    await session.execute(
        update(DecisionRow).where(DecisionRow.workspace == old).values(workspace=new)
    )
    await session.execute(
        update(OutcomeRow).where(OutcomeRow.workspace == old).values(workspace=new)
    )
    await session.execute(
        update(RuntimeSessionRow)
        .where(RuntimeSessionRow.workspace == old)
        .values(workspace=new)
    )
    await session.execute(
        update(WorkspaceConfigRow)
        .where(WorkspaceConfigRow.workspace == old)
        .values(workspace=new)
    )
    await session.execute(
        update(ConnectorConfigRow)
        .where(ConnectorConfigRow.workspace == old)
        .values(workspace=new)
    )
    row = await session.get(WorkspaceRow, old)
    if row is not None:
        session.add(WorkspaceRow(name=new, created_at=row.created_at))
        await session.delete(row)


class WorkflowDefinitionStore:
    """Workspace-scoped CRUD over saved workflow definitions."""

    def __init__(self, session: AsyncSession, workspace: str = "default") -> None:
        self._session = session
        self._workspace = workspace

    def _to_model(self, row: WorkflowDefinitionRow) -> WorkflowDefinition:
        return WorkflowDefinition.model_validate(row.payload)

    async def list(self) -> _L[WorkflowDefinition]:
        rows = (
            (
                await self._session.execute(
                    select(WorkflowDefinitionRow)
                    .where(WorkflowDefinitionRow.workspace == self._workspace)
                    .order_by(
                        WorkflowDefinitionRow.is_default.desc(),
                        WorkflowDefinitionRow.name,
                    )
                )
            )
            .scalars()
            .all()
        )
        return [self._to_model(r) for r in rows]

    async def get(self, name: str) -> WorkflowDefinition | None:
        row = await self._session.get(WorkflowDefinitionRow, (self._workspace, name))
        return self._to_model(row) if row is not None else None

    async def save(
        self, defn: WorkflowDefinition, *, is_default: bool | None = None
    ) -> WorkflowDefinition:
        existing = await self._session.get(
            WorkflowDefinitionRow, (self._workspace, defn.name)
        )
        default_flag = (
            is_default
            if is_default is not None
            else (existing.is_default if existing is not None else False)
        )
        await self._session.merge(
            WorkflowDefinitionRow(
                workspace=self._workspace,
                name=defn.name,
                title=defn.title,
                payload=defn.model_dump(mode="json"),
                builtin=defn.builtin,
                is_default=default_flag,
                updated_at=_now(),
            )
        )
        await self._session.commit()
        return defn

    async def delete(self, name: str) -> None:
        row = await self._session.get(WorkflowDefinitionRow, (self._workspace, name))
        if row is None:
            return
        if row.builtin:
            raise ValueError(f"cannot delete built-in workflow: {name}")
        was_default = row.is_default
        await self._session.delete(row)
        if was_default:
            # Deleting the current default must not silently leave no default
            # (list()'s default-first ordering would then fall back to
            # whichever row sorts first alphabetically). Reassign to the
            # builtin, which always exists and is never deletable.
            builtin = (
                await self._session.execute(
                    select(WorkflowDefinitionRow).where(
                        WorkflowDefinitionRow.workspace == self._workspace,
                        WorkflowDefinitionRow.builtin.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if builtin is not None:
                builtin.is_default = True
        await self._session.commit()

    async def set_default(self, name: str) -> None:
        rows = (
            (
                await self._session.execute(
                    select(WorkflowDefinitionRow).where(
                        WorkflowDefinitionRow.workspace == self._workspace
                    )
                )
            )
            .scalars()
            .all()
        )
        if not any(r.name == name for r in rows):
            raise ValueError(f"no such workflow: {name}")
        for r in rows:
            r.is_default = r.name == name
        await self._session.commit()

    async def get_default(self) -> WorkflowDefinition | None:
        row = (
            await self._session.execute(
                select(WorkflowDefinitionRow)
                .where(WorkflowDefinitionRow.workspace == self._workspace)
                .where(WorkflowDefinitionRow.is_default.is_(True))
            )
        ).scalar_one_or_none()
        return self._to_model(row) if row is not None else None

    async def ensure_default(self, defn: WorkflowDefinition) -> None:
        existing = (
            await self._session.execute(
                select(WorkflowDefinitionRow.name).where(
                    WorkflowDefinitionRow.workspace == self._workspace
                )
            )
        ).first()
        if existing is not None:
            return
        await self._session.merge(
            WorkflowDefinitionRow(
                workspace=self._workspace,
                name=defn.name,
                title=defn.title,
                payload=defn.model_dump(mode="json"),
                builtin=True,
                is_default=True,
                updated_at=_now(),
            )
        )
        await self._session.commit()
