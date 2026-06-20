import pytest
from pydantic import ValidationError

from productagents.schemas import (
    AnalystFindings,
    AnalystReport,
    DecisionRecord,
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


def test_risk_finding_holds_level_and_rationale():
    from productagents.schemas import RiskFinding

    finding = RiskFinding(level="high", rationale="tight deadline")
    assert finding.level == "high"
    assert finding.rationale == "tight deadline"


def test_risk_assessment_defaults_not_failed():
    from productagents.schemas import RiskAssessment

    assessment = RiskAssessment(
        reviewer="delivery",
        role="Delivery Risk Reviewer",
        level="medium",
        rationale="some integration work",
    )
    assert assessment.reviewer == "delivery"
    assert assessment.failed is False


def test_decision_record_defaults_to_empty_risks():
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
    assert record.risks == []


def test_decision_record_round_trips_with_risks():
    from productagents.schemas import (
        DecisionRecord,
        Initiative,
        Recommendation,
        RiskAssessment,
    )

    record = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        risks=[
            RiskAssessment(
                reviewer="financial",
                role="Financial Risk Reviewer",
                level="low",
                rationale="cheap to build",
            )
        ],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    restored = DecisionRecord.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.risks[0].reviewer == "financial"


def test_governance_finding_holds_verdict_and_rationale():
    from productagents.schemas import GovernanceFinding

    finding = GovernanceFinding(verdict="approve", rationale="best use of budget")
    assert finding.verdict == "approve"
    assert finding.rationale == "best use of budget"


def test_governance_verdict_defaults_not_failed():
    from productagents.schemas import GovernanceVerdict

    verdict = GovernanceVerdict(verdict="reject", rationale="too risky right now")
    assert verdict.verdict == "reject"
    assert verdict.failed is False


def test_decision_record_defaults_to_none_governance():
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
    assert record.governance is None


def test_decision_record_round_trips_with_governance():
    from productagents.schemas import (
        DecisionRecord,
        GovernanceVerdict,
        Initiative,
        Recommendation,
    )

    record = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        governance=GovernanceVerdict(
            verdict="request_analysis", rationale="need more data"
        ),
        timestamp="2026-06-19T12:00:00+00:00",
    )
    restored = DecisionRecord.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.governance.verdict == "request_analysis"


def test_reflection_holds_outcome_fields():
    from productagents.schemas import Reflection

    r = Reflection(
        actual_outcomes=["slow adoption"],
        prediction_accuracy=0.4,
        lessons_learned=["validate demand earlier"],
    )
    assert r.actual_outcomes == ["slow adoption"]
    assert r.prediction_accuracy == 0.4
    assert r.lessons_learned == ["validate demand earlier"]


def test_reflection_accuracy_must_be_in_range():
    from productagents.schemas import Reflection

    with pytest.raises(ValidationError):
        Reflection(actual_outcomes=[], prediction_accuracy=1.5, lessons_learned=[])


def test_outcome_record_accuracy_must_be_in_range():
    from productagents.schemas import OutcomeRecord

    with pytest.raises(ValidationError):
        OutcomeRecord(
            decision_id="d1",
            actual_outcomes=[],
            prediction_accuracy=1.5,
            lessons_learned=[],
            reflected_at="2026-06-20T00:00:00+00:00",
        )


def test_outcome_record_defaults_not_failed():
    from productagents.schemas import OutcomeRecord

    o = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=[],
        prediction_accuracy=0.0,
        lessons_learned=[],
        reflected_at="2026-06-20T00:00:00+00:00",
    )
    assert o.decision_id == "d1"
    assert o.failed is False


def test_outcome_record_round_trips():
    from productagents.schemas import OutcomeRecord

    o = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["x"],
        prediction_accuracy=0.7,
        lessons_learned=["y"],
        reflected_at="2026-06-20T00:00:00+00:00",
    )
    restored = OutcomeRecord.model_validate_json(o.model_dump_json())
    assert restored == o


def test_decision_record_keeps_explicit_id():
    from productagents.schemas import DecisionRecord, Initiative, Recommendation

    rec = DecisionRecord(
        decision_id="fixed-id",
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    restored = DecisionRecord.model_validate_json(rec.model_dump_json())
    assert restored.decision_id == "fixed-id"


def test_decision_record_generates_id_by_default():
    from productagents.schemas import DecisionRecord, Initiative, Recommendation

    rec = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    assert isinstance(rec.decision_id, str)
    assert rec.decision_id
