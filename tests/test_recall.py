from productagents.agents.recall import recall_node
from productagents.core.schemas import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)


def _state_with_history():
    decision = DecisionRecord(
        decision_id="d1",
        initiative=Initiative(title="Add enterprise SSO login", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    outcome = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["shipped late"],
        prediction_accuracy=0.5,
        lessons_learned=["SSO integrations take longer than predicted"],
        reflected_at="2026-06-20T00:00:00+00:00",
    )
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "portfolio": [decision],
        "outcomes": [outcome],
    }


async def test_recall_surfaces_relevant_lessons():
    result = await recall_node(_state_with_history())
    lessons = result["prior_lessons"]
    assert any("take longer than predicted" in line for line in lessons)


async def test_recall_empty_without_history():
    state = {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "portfolio": [],
        "outcomes": [],
    }
    result = await recall_node(state)
    assert result["prior_lessons"] == []


async def test_recall_tolerates_missing_state_keys():
    # No portfolio/outcomes keys at all — must default, not KeyError.
    state = {"initiative": Initiative(title="Add SSO", description="Enterprise SSO")}
    result = await recall_node(state)
    assert result["prior_lessons"] == []


async def test_recall_degrades_on_error(monkeypatch):
    from productagents.agents import recall as recall_module

    def boom(*_args, **_kwargs):
        raise RuntimeError("retrieval blew up")

    monkeypatch.setattr(recall_module, "select_relevant_lessons", boom)
    result = await recall_node(_state_with_history())
    assert result["prior_lessons"] == []
