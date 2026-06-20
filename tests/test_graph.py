from productagents.graph import build_graph
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    Initiative,
    Recommendation,
    RiskFinding,
)
from tests.fakes import FakeChatModel


def _model():
    return FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["finding"], signals=["signal"]),
            DebateArgument: DebateArgument(argument="my argument"),
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.75,
                rationale="evidence supports it",
                expected_outcomes=["growth"],
            ),
            RiskFinding: RiskFinding(level="medium", rationale="manageable risk"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="best use of resources"
            ),
        }
    )


def _initial_state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "evidence": Evidence(
            scenario="sample",
            customer_feedback="demand",
            product_analytics={"x": 1},
        ),
        "reports": [],
        "debate": [],
        "recommendation": None,
        "risks": [],
        "portfolio": [],
        "governance": None,
    }


async def test_graph_runs_through_governance(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    graph = build_graph(_model())
    final = await graph.ainvoke(_initial_state())

    assert len(final["reports"]) == 5
    analysts = {r.analyst for r in final["reports"]}
    assert analysts == {
        "customer_research",
        "product_analytics",
        "market",
        "business",
        "technical",
    }

    assert [(t.round, t.side) for t in final["debate"]] == [
        (1, "advocate"),
        (1, "skeptic"),
        (2, "advocate"),
        (2, "skeptic"),
    ]

    assert final["recommendation"].recommendation == "Build it"

    assert [r.reviewer for r in final["risks"]] == [
        "delivery",
        "adoption",
        "strategic",
        "financial",
        "organizational",
    ]

    assert final["governance"].verdict == "approve"
