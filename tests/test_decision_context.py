"""Decision-context models live in core.models.decision and reuse planning.Initiative.
"""

from productagents.core.models.decision import DecisionRecord, Recommendation
from productagents.core.models.planning import Initiative


def test_decision_record_uses_planning_initiative():
    rec = DecisionRecord(
        initiative=Initiative(title="Add SSO", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.8,
            rationale="strong demand",
            expected_outcomes=["enterprise unblock"],
        ),
        reports=[],
        timestamp="2026-06-23T12:00:00+00:00",
    )
    assert isinstance(rec.initiative, Initiative)
    assert DecisionRecord.model_validate_json(rec.model_dump_json()) == rec


def test_decision_record_generates_id_by_default():
    def make() -> DecisionRecord:
        return DecisionRecord(
            initiative=Initiative(title="t", description="d"),
            recommendation=Recommendation(
                recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
            ),
            reports=[],
            timestamp="2026-06-23T12:00:00+00:00",
        )

    assert make().decision_id != make().decision_id
