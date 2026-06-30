"""DecisionReadService — read past decisions and their reflections for presentation.

The read face of the DecisionStore (the decision system-of-record). Presentation
lists decisions and opens one through this service, never touching pa-memory
directly. Complements SessionService: SessionService replays *execution* (the
event log); this replays *decisions* (recommendation + predicted/actual outcomes).
"""

from __future__ import annotations

from productagents.core.models import DecisionRecord, OutcomeRecord

_L = list  # ponytail: 'list' method shadows the builtin under ty; alias keeps it honest


class DecisionReadService:
    def __init__(self, store_opener) -> None:
        # store_opener: Callable[..., AbstractAsyncContextManager[DecisionStore]]
        self._open = store_opener

    @classmethod
    def create(cls) -> DecisionReadService:
        from productagents.platform.context import open_decision_store

        return cls(open_decision_store)

    async def list(self) -> _L[DecisionRecord]:
        async with self._open() as store:
            return await store.decisions()

    async def get(
        self, decision_id: str
    ) -> tuple[DecisionRecord | None, _L[OutcomeRecord]]:
        async with self._open() as store:
            decisions = await store.decisions()
            outcomes = await store.outcomes()
        record = next((d for d in decisions if d.decision_id == decision_id), None)
        if record is None:
            return None, []
        return record, [o for o in outcomes if o.decision_id == decision_id]

    async def export(self, directory) -> tuple[int, int]:
        """Write decisions.jsonl + outcomes.jsonl to ``directory``; return counts.

        The DB is the system of record; this is the export/audit dump
        (productagents.memory.jsonl). Existing files are overwritten.
        """
        from pathlib import Path

        from productagents.memory import jsonl

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        async with self._open() as store:
            decisions = await store.decisions()
            outcomes = await store.outcomes()
        dpath = directory / "decisions.jsonl"
        opath = directory / "outcomes.jsonl"
        dpath.unlink(missing_ok=True)
        opath.unlink(missing_ok=True)
        for d in decisions:
            jsonl.record_decision(d, dpath)
        for o in outcomes:
            jsonl.record_outcome(o, opath)
        return len(decisions), len(outcomes)
