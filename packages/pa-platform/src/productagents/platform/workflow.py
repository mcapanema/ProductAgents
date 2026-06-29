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

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from productagents.platform import events as ev
from productagents.platform.session import Session

_L = list  # ponytail: 'list' method shadows the builtin under ty; alias keeps it honest


@dataclass(frozen=True)
class Workflow:
    """Metadata + a runner for one workflow.

    ``start`` returns ``(Session, AsyncIterator[Event])`` — the same contract
    ``DecisionService.start_session`` already produces. Each workflow defines its
    own ``start`` signature; the caller (which picks the workflow) passes inputs.
    """

    name: str
    title: str
    description: str
    start: Callable[..., tuple[Session, AsyncIterator[ev.Event]]]


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
    ) -> WorkflowService:
        """Build the default registry: the ``evaluate_initiative`` workflow wired
        to a ``DecisionService`` over ``model``."""
        from productagents.platform.decision_service import DecisionService

        service = DecisionService.for_model(
            model,
            recorder=recorder,
            human_in_the_loop=human_in_the_loop,
            persist_events=persist_events,
        )
        return cls(
            [
                Workflow(
                    name="evaluate_initiative",
                    title="Evaluate Initiative",
                    description=(
                        "Advisory pipeline: evidence → analysts → debate → "
                        "strategist → judge → risk → governance."
                    ),
                    start=service.start_session,
                )
            ]
        )

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
