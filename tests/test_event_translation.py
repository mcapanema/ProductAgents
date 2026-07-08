"""Dedicated coverage for the pure runner→platform event translation seam."""

from types import SimpleNamespace

import pytest

from productagents.agents import runner as rn
from productagents.core.models import (
    AnalystReport,
    Recommendation,
    RiskAssessment,
)
from productagents.platform import _event_translation as xl
from productagents.platform import events as ev

_SESSION = SimpleNamespace(id="s1")


def _rec() -> Recommendation:
    return Recommendation(
        recommendation="Build it",
        confidence=0.7,
        rationale="r",
        expected_outcomes=["o"],
    )


def _report() -> AnalystReport:
    return AnalystReport(
        analyst="market", role="market analyst", findings=["f"], signals=["s"]
    )


# (runner event, expected platform Event type, field name on both to compare)
_CASES = [
    (rn.ProgressEvent(node="market", message="thinking"), ev.NodeProgress, "message"),
    (
        rn.NodeCompleteEvent(node="market", report=_report()),
        ev.AnalystCompleted,
        "node",
    ),
    (
        rn.DebateTurnEvent(round=1, side="advocate", argument="a"),
        ev.DebateTurnEmitted,
        "argument",
    ),
    (
        rn.RiskAssessmentEvent(reviewer="r", role="sec", level="low", rationale="ok"),
        ev.RiskAssessed,
        "level",
    ),
    (rn.RecommendationEvent(recommendation=_rec()), ev.Recommended, "recommendation"),
    (
        rn.JudgmentEvent(
            evidence_grounding_score=0.9,
            rationale_coherence_score=0.8,
            passed=True,
            critique="c",
            attempt=1,
        ),
        ev.Judged,
        "critique",
    ),
    (
        rn.GovernanceVerdictEvent(verdict="approve", rationale="ok"),
        ev.GovernanceAdvised,
        "verdict",
    ),
    (rn.RecallEvent(lessons=["l1"]), ev.LessonsRecalled, "lessons"),
    (rn.NodeErrorEvent(node="risk", message="boom"), ev.NodeFailed, "message"),
    (
        rn.RunAbortedEvent(node="strategist", category="rate_limit", message="429"),
        ev.SessionFailed,
        "category",
    ),
    (
        rn.FinalVerdictEvent(verdict="approve", rationale="ok", decided_by="human"),
        ev.FinalVerdict,
        "decided_by",
    ),
]


@pytest.mark.parametrize(("source", "expected_type", "field"), _CASES)
def test_translate_maps_each_runner_event(source, expected_type, field):
    factory = xl.translate(_SESSION, source)
    assert factory is not None
    event = factory(7)
    assert isinstance(event, expected_type)
    assert event.session_id == "s1"
    assert event.seq == 7
    assert getattr(event, field) == getattr(source, field)


def test_translate_finished_event_carries_every_bundle_field():
    source = rn.FinishedEvent(
        recommendation=_rec(),
        reports=[_report()],
        debate=[],
        risks=[RiskAssessment(reviewer="r", role="sec", level="low", rationale="ok")],
        governance=None,
        prior_lessons=["l"],
        judgment=None,
    )
    factory = xl.translate(_SESSION, source)
    assert factory is not None
    event = factory(3)
    assert isinstance(event, ev.SessionFinished)
    assert event.recommendation == source.recommendation
    assert event.reports == source.reports
    assert event.risks == source.risks
    assert event.prior_lessons == ["l"]


def test_translate_unknown_event_returns_none():
    assert xl.translate(_SESSION, object()) is None


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        (
            ev.ApprovalRequested(
                session_id="s1",
                seq=0,
                advisory_verdict="approve",
                advisory_rationale="r",
            ),
            "awaiting_approval",
        ),
        (ev.SessionCancelled(session_id="s1", seq=0), "cancelled"),
        (ev.NodeProgress(session_id="s1", seq=0, node="market", message="m"), None),
        (
            ev.SessionFinished(
                session_id="s1",
                seq=0,
                recommendation=_rec(),
                reports=[_report()],
                debate=[],
                risks=[],
                governance=None,
                prior_lessons=[],
                judgment=None,
            ),
            "finished",
        ),
        (
            ev.SessionFailed(
                session_id="s1",
                seq=0,
                node="strategist",
                category="rate_limit",
                message="429",
            ),
            "failed",
        ),
    ],
)
def test_status_for_maps_terminal_events(event, expected):
    assert xl.status_for(event) == expected
