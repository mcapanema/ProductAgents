import pytest
from pydantic import ValidationError

from productagents.schemas import (
    AnalystFindings,
    AnalystReport,
    DecisionRecord,
    Evidence,
    Initiative,
    Recommendation,
)


def test_initiative_fields():
    init = Initiative(title="Add SSO", description="Enterprise single sign-on")
    assert init.title == "Add SSO"
    assert init.description == "Enterprise single sign-on"


def test_analyst_report_defaults_not_failed():
    report = AnalystReport(
        analyst="customer_research",
        role="Customer Research Analyst",
        findings=["users want SSO"],
        signals=["12 enterprise tickets"],
    )
    assert report.failed is False


def test_recommendation_confidence_must_be_in_range():
    with pytest.raises(ValidationError):
        Recommendation(
            recommendation="Build it",
            confidence=1.5,
            rationale="because",
            expected_outcomes=["higher retention"],
        )


def test_decision_record_round_trips_through_json():
    record = DecisionRecord(
        initiative=Initiative(title="Add SSO", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.8,
            rationale="strong demand",
            expected_outcomes=["enterprise unblock"],
        ),
        reports=[
            AnalystReport(
                analyst="product_analytics",
                role="Product Analytics Analyst",
                findings=["login drop-off"],
                signals=["30% churn at auth"],
            )
        ],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    dumped = record.model_dump_json()
    restored = DecisionRecord.model_validate_json(dumped)
    assert restored == record


def test_analyst_findings_holds_lists():
    findings = AnalystFindings(findings=["a"], signals=["b"])
    assert findings.findings == ["a"]
    assert findings.signals == ["b"]


def test_debate_turn_fields():
    from productagents.schemas import DebateTurn

    turn = DebateTurn(round=1, side="advocate", argument="We should build it.")
    assert turn.round == 1
    assert turn.side == "advocate"
    assert turn.argument == "We should build it."


def test_debate_argument_holds_text():
    from productagents.schemas import DebateArgument

    arg = DebateArgument(argument="Risk is too high.")
    assert arg.argument == "Risk is too high."


def test_decision_record_defaults_to_empty_debate():
    from productagents.schemas import (
        DecisionRecord,
        Initiative,
        Recommendation,
    )

    record = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    assert record.debate == []


def test_decision_record_round_trips_with_debate():
    from productagents.schemas import (
        DebateTurn,
        DecisionRecord,
        Initiative,
        Recommendation,
    )

    record = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        debate=[
            DebateTurn(round=1, side="advocate", argument="for"),
            DebateTurn(round=1, side="skeptic", argument="against"),
        ],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    restored = DecisionRecord.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.debate[1].side == "skeptic"
