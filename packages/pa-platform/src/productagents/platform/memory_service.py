"""MemoryService — read the organizational-memory lesson corpus for browsing.

A presentation-shaped read face over the DecisionStore: it flattens past
decisions + their reflected outcomes into Lesson records (validated outcome
lessons first, then prediction-style derived lessons). Distinct from
DecisionReadService (which replays one decision's predicted vs actual) — this
is the cross-decision lesson list the Organizational Memory panel renders.
"""

from __future__ import annotations

from dataclasses import dataclass

from productagents.core._typing import List as _L


@dataclass(frozen=True)
class Lesson:
    decision_id: str
    title: str
    text: str
    validated: bool
    prediction_accuracy: float | None


class MemoryService:
    def __init__(self, store_opener) -> None:
        # store_opener: Callable[..., AbstractAsyncContextManager[DecisionStore]]
        self._open = store_opener

    @classmethod
    def create(cls, workspace: str = "default") -> MemoryService:
        from functools import partial

        from productagents.platform.context import open_decision_store

        return cls(partial(open_decision_store, workspace=workspace))

    async def lessons(self, *, limit: int = 50) -> _L[Lesson]:
        async with self._open() as store:
            decisions = await store.decisions()  # oldest first
            outcomes = await store.outcomes()
        by_id = {}
        for o in outcomes:
            if not o.failed and o.lessons_learned:
                by_id.setdefault(o.decision_id, o)
        out: _L[Lesson] = []
        for d in reversed(decisions):  # newest first
            o = by_id.get(d.decision_id)
            if o is not None:
                for text in o.lessons_learned:
                    out.append(
                        Lesson(
                            decision_id=d.decision_id,
                            title=d.initiative.title,
                            text=text,
                            validated=True,
                            prediction_accuracy=o.prediction_accuracy,
                        )
                    )
            elif not d.recommendation.failed:
                rec = d.recommendation
                out.append(
                    Lesson(
                        decision_id=d.decision_id,
                        title=d.initiative.title,
                        text=(
                            f'Decided "{rec.recommendation}" '
                            f"({rec.confidence:.0%} confidence): {rec.rationale}"
                        ),
                        validated=False,
                        prediction_accuracy=None,
                    )
                )
        return out[:limit]
