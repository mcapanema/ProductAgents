"""Tests for DecisionReadService — the presentation read face of the DecisionStore."""

from contextlib import asynccontextmanager

from productagents.core.models import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)
from productagents.platform.decision_read_service import DecisionReadService


class _FakeStore:
    """In-memory stand-in for DecisionStore."""

    def __init__(self, decisions=(), outcomes=()):
        self._decisions = list(decisions)
        self._outcomes = list(outcomes)

    async def decisions(self):
        return self._decisions

    async def outcomes(self):
        return self._outcomes


def _opener(store):
    @asynccontextmanager
    async def _open(*, engine=None):
        yield store

    return _open


def _record(decision_id="d1", title="New API"):
    return DecisionRecord(
        decision_id=decision_id,
        initiative=Initiative(title=title, description=title),
        recommendation=Recommendation(
            recommendation="ship it",
            confidence=0.8,
            rationale="because",
            expected_outcomes=["adoption up"],
        ),
        reports=[],
        timestamp="2026-06-28T00:00:00+00:00",
    )


def _outcome(decision_id="d1"):
    return OutcomeRecord(
        decision_id=decision_id,
        actual_outcomes=["adoption flat"],
        prediction_accuracy=0.4,
        lessons_learned=["scope smaller"],
        reflected_at="2026-06-29T00:00:00+00:00",
    )


async def test_list_returns_all_decisions():
    svc = DecisionReadService(_opener(_FakeStore([_record("a"), _record("b")])))
    rows = await svc.list()
    assert [r.decision_id for r in rows] == ["a", "b"]


async def test_get_returns_record_and_its_outcomes():
    store = _FakeStore(
        decisions=[_record("d1"), _record("d2")],
        outcomes=[_outcome("d1"), _outcome("d2"), _outcome("d1")],
    )
    svc = DecisionReadService(_opener(store))
    record, outcomes = await svc.get("d1")
    assert record is not None
    assert record.decision_id == "d1"
    assert [o.decision_id for o in outcomes] == ["d1", "d1"]


async def test_get_unknown_id_returns_none_and_empty():
    svc = DecisionReadService(_opener(_FakeStore([_record("d1")])))
    record, outcomes = await svc.get("missing")
    assert record is None
    assert outcomes == []
