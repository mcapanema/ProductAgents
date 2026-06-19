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
