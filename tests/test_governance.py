from productagents.core.schemas import (
    DecisionRecord,
    GovernanceFinding,
    GovernanceVerdict,
    Initiative,
    Recommendation,
    RiskAssessment,
)

from productagents.agents.governance import _format_portfolio, governance_node
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "recommendation": Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="strong demand",
            expected_outcomes=["growth"],
        ),
        "risks": [
            RiskAssessment(
                reviewer="delivery",
                role="Delivery Risk Reviewer",
                level="medium",
                rationale="some integration work",
            )
        ],
        "portfolio": [],
    }


def _prior_record(title: str, verdict: str) -> DecisionRecord:
    return DecisionRecord(
        initiative=Initiative(title=title, description="d"),
        recommendation=Recommendation(
            recommendation="ship", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        governance=GovernanceVerdict(verdict=verdict, rationale="prior"),
        timestamp="2026-06-19T12:00:00+00:00",
    )


def test_format_portfolio_handles_empty():
    assert _format_portfolio([]) == "(no prior decisions)"


def test_format_portfolio_summarizes_prior_decisions():
    summary = _format_portfolio([_prior_record("Old Feature", "approve")])
    assert "Old Feature" in summary
    assert "approve" in summary


async def test_governance_node_produces_verdict():
    model = FakeChatModel(
        {GovernanceFinding: GovernanceFinding(verdict="approve", rationale="worth it")}
    )
    result = await governance_node(_state(), model)
    verdict = result["governance"]
    assert verdict.verdict == "approve"
    assert verdict.rationale == "worth it"
    assert verdict.failed is False


async def test_governance_node_degrades_on_failure():
    model = FakeChatModel({GovernanceFinding: RuntimeError("LLM down")})
    result = await governance_node(_state(), model)
    verdict = result["governance"]
    assert verdict.failed is True
    assert verdict.verdict == "error"
    assert "unavailable" in verdict.rationale


async def test_governance_degrades_when_model_returns_none():
    model = FakeChatModel({GovernanceFinding: None})
    state = {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "recommendation": Recommendation(
            recommendation="ship", confidence=0.5, rationale="r", expected_outcomes=[]
        ),
        "risks": [],
        "portfolio": [],
    }
    result = await governance_node(state, model)
    verdict = result["governance"]
    assert verdict.failed is True
    assert verdict.verdict == "error"
