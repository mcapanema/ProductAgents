from datetime import UTC, datetime

from productagents.core.models import (
    AnalystReport,
    DebateTurn,
    GovernanceVerdict,
    JudgeVerdict,
    Recommendation,
    RiskAssessment,
)
from productagents.platform import events as ev
from productagents.platform.serialization import deserialize_event, serialize_event

_TS = datetime(2026, 6, 28, 12, 0, 0, tzinfo=UTC)


def _rec() -> Recommendation:
    return Recommendation(
        recommendation="Build it",
        confidence=0.7,
        rationale="r",
        expected_outcomes=["o"],
    )


def _report() -> AnalystReport:
    # ponytail: role is required on AnalystReport (brief omitted it)
    return AnalystReport(
        analyst="market", role="market analyst", findings=["f"], signals=["s"]
    )


def _all_events() -> list[ev.Event]:
    """One instance of every concrete Event subclass (explicit so a newly added
    event without a sample here trips the count assertion below)."""
    return [
        ev.SessionStarted(
            session_id="s", seq=0, ts=_TS, workflow="evaluate_initiative"
        ),
        ev.NodeProgress(
            session_id="s", seq=1, ts=_TS, node="market", message="thinking"
        ),
        ev.AnalystCompleted(
            session_id="s", seq=2, ts=_TS, node="market", report=_report()
        ),
        ev.DebateTurnEmitted(
            session_id="s", seq=3, ts=_TS, round=1, side="advocate", argument="a"
        ),
        ev.RiskAssessed(
            session_id="s",
            seq=4,
            ts=_TS,
            reviewer="r",
            role="sec",
            level="low",
            rationale="ok",
        ),
        ev.Recommended(session_id="s", seq=5, ts=_TS, recommendation=_rec()),
        ev.Judged(
            session_id="s",
            seq=6,
            ts=_TS,
            passed=True,
            evidence_grounding_score=0.9,
            rationale_coherence_score=0.9,
            critique="ok",
            attempt=1,
        ),
        ev.GovernanceAdvised(
            session_id="s", seq=7, ts=_TS, verdict="approve", rationale="ok"
        ),
        ev.LessonsRecalled(session_id="s", seq=8, ts=_TS, lessons=["l1", "l2"]),
        ev.ApprovalRequested(
            session_id="s",
            seq=9,
            ts=_TS,
            advisory_verdict="approve",
            advisory_rationale="ok",
        ),
        ev.FinalVerdict(
            session_id="s",
            seq=10,
            ts=_TS,
            verdict="approve",
            rationale="ok",
            decided_by="human",
        ),
        ev.NodeFailed(session_id="s", seq=11, ts=_TS, node="risk", message="transient"),
        ev.SessionFailed(
            session_id="s",
            seq=12,
            ts=_TS,
            node="strategist",
            category="rate_limit",
            message="429",
        ),
        ev.SessionFinished(
            session_id="s",
            seq=13,
            ts=_TS,
            recommendation=_rec(),
            reports=[_report()],
            debate=[DebateTurn(round=1, side="advocate", argument="a")],
            risks=[
                RiskAssessment(reviewer="r", role="sec", level="low", rationale="ok")
            ],
            governance=GovernanceVerdict(verdict="approve", rationale="ok"),
            prior_lessons=["l"],
            judgment=JudgeVerdict(
                passed=True,
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="ok",
                attempt=1,
            ),
        ),
    ]


def test_every_event_subclass_has_a_sample():
    """Guard: every concrete Event subclass is exercised below. A new event type
    forces an entry in _all_events()."""
    sampled = {type(e).__name__ for e in _all_events()}
    declared = {c.__name__ for c in ev.Event.__subclasses__()}
    assert sampled == declared


def test_round_trip_preserves_every_event():
    for original in _all_events():
        event_type, payload = serialize_event(original)
        assert event_type == type(original).__name__
        assert isinstance(payload, dict)
        restored = deserialize_event(event_type, payload)
        assert restored == original


def test_payload_is_json_safe():
    """Payload must be plain JSON types (the value stored in the JSON column)."""
    import json

    _, payload = serialize_event(_all_events()[-1])  # SessionFinished — richest
    assert json.loads(json.dumps(payload)) == payload
