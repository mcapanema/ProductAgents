"""WorkflowService — workflows as first-class, registered citizens.

A workflow is a named, described pipeline the platform can run. Today there is
exactly one — ``evaluate_initiative`` — but presentation now selects it *by name*
from a registry instead of calling ``DecisionService`` directly. Adding a future
workflow (roadmap prioritization, quarterly planning, …) is registration, not a
new service call: build its ``Workflow`` and hand it to ``WorkflowService``.

``WorkflowService`` is a thin router. The decision pipeline's real work still
lives in ``DecisionService``; this layer maps a name to that work.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from productagents.platform import events as ev
from productagents.platform.session import Session

logger = logging.getLogger(__name__)

_L = list  # ponytail: 'list' method shadows the builtin under ty; alias keeps it honest


@dataclass(frozen=True)
class Workflow:
    """Metadata + a runner for one workflow.

    ``start`` returns ``(Session, AsyncIterator[Event])`` — the same contract
    ``DecisionService.start_session`` already produces. Each workflow defines its
    own ``start`` signature; the caller (which picks the workflow) passes inputs.

    ``topology`` (optional) returns the workflow's graph structure as plain
    ``{nodes, edges}`` dicts for presentation (the GUI's Workflows panel).
    """

    name: str
    title: str
    description: str
    start: Callable[..., tuple[Session, AsyncIterator[ev.Event]]]
    cancel: Callable[[str], bool] | None = None
    topology: Callable[[], dict] | None = None


def build_evaluate_initiative(
    model,
    *,
    recorder=None,
    human_in_the_loop: bool = False,
    persist_events: bool = True,
    workspace: str = "default",
) -> Workflow:
    """Build the advisory decision pipeline as a Workflow over ``model``.

    The first-party ``productagents.workflows`` entry point resolves here.
    """
    from productagents.agents.topology import graph_topology
    from productagents.platform.decision_service import DecisionService

    service = DecisionService.for_model(
        model,
        recorder=recorder,
        human_in_the_loop=human_in_the_loop,
        persist_events=persist_events,
        workspace=workspace,
    )
    return Workflow(
        name="evaluate_initiative",
        title="Evaluate Initiative",
        description=(
            "Weighs a product initiative through five analyst perspectives at once — "
            "customer, analytics, market, business and technical — then has an "
            "advocate and skeptic debate it, synthesizes a recommendation, and "
            "stress-tests it through judge, risk and governance review before "
            "advising a decision."
        ),
        start=service.start_session,
        cancel=service.cancel,
        topology=lambda: graph_topology(human_in_the_loop=human_in_the_loop),
    )


class WorkflowService:
    def __init__(self, workflows: _L[Workflow]) -> None:
        self._workflows: dict[str, Workflow] = {w.name: w for w in workflows}

    @classmethod
    def for_model(
        cls,
        model,
        *,
        recorder=None,
        human_in_the_loop: bool = False,
        persist_events: bool = True,
        workspace: str = "default",
    ) -> WorkflowService:
        """Build the registry from every installed ``productagents.workflows``
        plugin. The first-party ``evaluate_initiative`` is one such plugin."""
        from productagents.platform.workflow_registry import discover

        built: _L[Workflow] = []
        for name, build in discover().items():
            try:
                built.append(
                    build(
                        model,
                        recorder=recorder,
                        human_in_the_loop=human_in_the_loop,
                        persist_events=persist_events,
                        workspace=workspace,
                    )
                )
            except Exception:  # noqa: BLE001 — one bad workflow must not break the rest
                logger.warning(
                    "workflow %r failed to build; skipping", name, exc_info=True
                )
        return cls(built)

    def list(self) -> _L[Workflow]:
        return list(self._workflows.values())

    def get(self, name: str) -> Workflow | None:
        return self._workflows.get(name)

    def run(
        self, name: str, *args, **kwargs
    ) -> tuple[Session, AsyncIterator[ev.Event]]:
        workflow = self._workflows.get(name)
        if workflow is None:
            raise KeyError(f"unknown workflow: {name!r}")
        return workflow.start(*args, **kwargs)

    def cancel(self, session_id: str) -> bool:
        """Ask every workflow to cancel the session; True if any owned it.

        ponytail: the session→workflow map isn't tracked (one workflow today);
        DecisionService.cancel is a no-op for sessions it doesn't own, so a
        fan-out is safe. Add a session index only when many workflows coexist.
        """
        return any(w.cancel(session_id) for w in self._workflows.values() if w.cancel)
