"""Tests for the `decisions.list` / `decisions.show` IPC methods."""

from productagents.app import ipc
from productagents.core.models import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)
from tests._ipc_helpers import _collect, _FakeSessions, _workflows


class _FakeDecisions:
    """Stand-in for DecisionReadService with in-memory rows."""

    def __init__(self, records=(), outcomes=None):
        self._records = list(records)
        self._outcomes = outcomes or {}

    async def list(self):
        return self._records

    async def get(self, decision_id):
        record = next((r for r in self._records if r.decision_id == decision_id), None)
        if record is None:
            return None, []
        return record, self._outcomes.get(decision_id, [])


def _decision(decision_id="d1", title="New API"):
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


async def test_decisions_list_returns_summaries():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 10, "method": "decisions.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "decisions": _FakeDecisions([_decision("d1")]),
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 10,
            "result": [
                {
                    "id": "d1",
                    "title": "New API",
                    "recommendation": "ship it",
                    "confidence": 0.8,
                    "created_at": "2026-06-28T00:00:00+00:00",
                }
            ],
        }
    ]


async def test_decisions_show_returns_record_and_outcomes():
    outcome = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["flat"],
        prediction_accuracy=0.4,
        lessons_learned=["scope smaller"],
        reflected_at="2026-06-29T00:00:00+00:00",
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 11, "method": "decisions.show", "params": {"decision_id": "d1"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "decisions": _FakeDecisions([_decision("d1")], {"d1": [outcome]}),
        },
        emit=emit,
    )
    result = sink[0]["result"]
    assert sink[0]["id"] == 11
    assert result["record"]["decision_id"] == "d1"
    assert result["record"]["recommendation"]["recommendation"] == "ship it"
    assert result["outcomes"][0]["lessons_learned"] == ["scope smaller"]


async def test_decisions_show_unknown_id_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 12, "method": "decisions.show", "params": {"decision_id": "missing"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "decisions": _FakeDecisions([_decision("d1")]),
        },
        emit=emit,
    )
    assert sink == [{"id": 12, "error": "no such decision: missing"}]
