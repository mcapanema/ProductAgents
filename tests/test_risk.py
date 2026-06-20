from productagents.agents.risk import REVIEWERS, risk_node
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Initiative,
    Recommendation,
    RiskFinding,
)
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "reports": [
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["demand"],
                signals=["tickets"],
            )
        ],
        "debate": [DebateTurn(round=1, side="advocate", argument="build it")],
        "recommendation": Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="strong demand",
            expected_outcomes=["growth"],
        ),
    }


def test_reviewers_are_the_five_fixed_roles_in_order():
    assert [r[0] for r in REVIEWERS] == [
        "delivery",
        "adoption",
        "strategic",
        "financial",
        "organizational",
    ]


async def test_risk_node_produces_one_assessment_per_reviewer():
    model = FakeChatModel(
        {RiskFinding: RiskFinding(level="medium", rationale="some risk")}
    )
    result = await risk_node(_state(), model)
    risks = result["risks"]
    assert [r.reviewer for r in risks] == [
        "delivery",
        "adoption",
        "strategic",
        "financial",
        "organizational",
    ]
    assert all(r.level == "medium" for r in risks)
    assert all(r.rationale == "some risk" for r in risks)
    assert all(r.failed is False for r in risks)


async def test_risk_node_degrades_on_failure():
    model = FakeChatModel({RiskFinding: RuntimeError("LLM down")})
    result = await risk_node(_state(), model)
    risks = result["risks"]
    assert len(risks) == 5
    assert all(r.failed for r in risks)
    assert risks[0].level == "unknown"
    assert "unavailable" in risks[0].rationale
