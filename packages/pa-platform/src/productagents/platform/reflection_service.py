"""Application service for out-of-graph outcome reflection.

Ties the decision reader, the reflection agent, and the outcome recorder into a
single presentation-agnostic seam so the CLI (`productagents reflect`) and the
GUI (`reflection.record` IPC method) drive identical logic. This is the capture
half of Outcome Learning, which lives outside the decision graph.
"""

from __future__ import annotations

from functools import partial

from productagents.core.models import DecisionRecord, OutcomeRecord


class ReflectionService:
    def __init__(self, *, reflector, reader, recorder) -> None:
        # reflector: async (DecisionRecord, str) -> OutcomeRecord
        # reader:    async () -> list[DecisionRecord]
        # recorder:  async (OutcomeRecord) -> None
        self._reflect = reflector
        self._read = reader
        self._record = recorder

    @classmethod
    def for_model(cls, model, workspace: str = "default") -> ReflectionService:
        # Lazy imports keep platform.__init__ free of import-time cycles.
        from productagents.platform.context import (
            make_decision_reader,
            make_outcome_recorder,
        )
        from productagents.platform.reflection import reflect

        return cls(
            reflector=partial(reflect, model=model),
            reader=make_decision_reader(workspace=workspace),
            recorder=make_outcome_recorder(workspace=workspace),
        )

    async def decisions(self) -> list[DecisionRecord]:
        return await self._read()

    async def reflect_on(self, decision_id: str, note: str) -> OutcomeRecord:
        decisions = await self._read()
        decision = next((d for d in decisions if d.decision_id == decision_id), None)
        if decision is None:
            raise LookupError(f"no such decision: {decision_id}")
        outcome = await self._reflect(decision, note)
        # ponytail: persist whatever reflect() returns, including a degraded
        # failed=True outcome — matches the old TUI behavior. Filter on read if
        # failed reflections ever pollute lesson retrieval.
        await self._record(outcome)
        return outcome
