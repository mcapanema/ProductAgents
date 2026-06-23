from datetime import datetime

from productagents.core.schemas import (
    DecisionRecord,
    Initiative,
    Recommendation,
    Reflection,
)

from productagents.agents.reflection import reflect
from tests.fakes import FakeChatModel


def _decision():
    return DecisionRecord(
        decision_id="dec-1",
        initiative=Initiative(title="Add SSO", description="Enterprise SSO"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.8,
            rationale="demand",
            expected_outcomes=["enterprise unblock"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


async def test_reflect_produces_outcome_record():
    model = FakeChatModel(
        {
            Reflection: Reflection(
                actual_outcomes=["slow adoption"],
                prediction_accuracy=0.4,
                lessons_learned=["validate demand earlier"],
            )
        }
    )
    outcome = await reflect(_decision(), "We shipped but adoption was slow.", model)
    assert outcome.decision_id == "dec-1"
    assert outcome.actual_outcomes == ["slow adoption"]
    assert outcome.prediction_accuracy == 0.4
    assert outcome.lessons_learned == ["validate demand earlier"]
    assert outcome.failed is False
    assert outcome.reflected_at  # non-empty ISO timestamp
    parsed = datetime.fromisoformat(outcome.reflected_at)
    assert parsed.tzinfo is not None


async def test_reflect_degrades_on_failure():
    model = FakeChatModel({Reflection: RuntimeError("LLM down")})
    outcome = await reflect(_decision(), "note", model)
    assert outcome.failed is True
    assert outcome.prediction_accuracy == 0.0
    assert outcome.actual_outcomes == []
    assert "unavailable" in outcome.lessons_learned[0]
    assert outcome.decision_id == "dec-1"


async def test_reflect_degrades_when_model_returns_none():
    model = FakeChatModel({Reflection: None})
    decision = DecisionRecord(
        initiative=Initiative(title="Add SSO", description="Enterprise SSO"),
        recommendation=Recommendation(
            recommendation="ship", confidence=0.5, rationale="r", expected_outcomes=[]
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    outcome = await reflect(decision, "It shipped late.", model)
    assert outcome.failed is True
    assert outcome.prediction_accuracy == 0.0
