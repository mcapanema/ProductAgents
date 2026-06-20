from productagents.agents.strategist import strategist_node
from productagents.schemas import AnalystReport, Initiative, Recommendation
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "reports": [
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["strong enterprise demand"],
                signals=["18 tickets"],
            ),
            AnalystReport(
                analyst="product_analytics",
                role="Product Analytics Analyst",
                findings=["30% onboarding drop-off"],
                signals=["funnel data"],
            ),
        ],
    }


async def test_strategist_returns_recommendation():
    expected = Recommendation(
        recommendation="Build SSO this quarter",
        confidence=0.82,
        rationale="Demand plus measurable onboarding friction.",
        expected_outcomes=["unblock enterprise deals"],
    )
    model = FakeChatModel({Recommendation: expected})
    result = await strategist_node(_state(), model)
    assert result["recommendation"] == expected


async def test_strategist_failure_yields_zero_confidence():
    model = FakeChatModel({Recommendation: RuntimeError("LLM down")})
    result = await strategist_node(_state(), model)
    rec = result["recommendation"]
    assert rec.confidence == 0.0
    assert "unable" in rec.recommendation.lower()


async def test_strategist_includes_debate_in_prompt(monkeypatch):
    from productagents.agents import strategist as strategist_module
    from productagents.schemas import DebateTurn

    captured = {}

    def fake_format_debate(turns):
        captured["turns"] = turns
        return "DEBATE-BLOCK"

    monkeypatch.setattr(strategist_module, "_format_debate", fake_format_debate)

    state = _state()
    state["debate"] = [DebateTurn(round=1, side="advocate", argument="for it")]

    from productagents.schemas import Recommendation

    model = FakeChatModel(
        {
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            )
        }
    )
    result = await strategist_node(state, model)
    assert result["recommendation"].recommendation == "Build it"
    assert captured["turns"][0].side == "advocate"


async def test_strategist_includes_prior_lessons_in_prompt(monkeypatch):
    from productagents.agents import strategist as strategist_module

    captured = {}

    def fake_format_lessons(lessons):
        captured["lessons"] = lessons
        return "LESSONS-BLOCK"

    monkeypatch.setattr(strategist_module, "_format_lessons", fake_format_lessons)

    state = _state()
    state["prior_lessons"] = ['From "Add SSO login": SSO took two quarters']

    model = FakeChatModel(
        {
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            )
        }
    )
    result = await strategist_node(state, model)
    assert result["recommendation"].recommendation == "Build it"
    assert captured["lessons"] == ['From "Add SSO login": SSO took two quarters']
