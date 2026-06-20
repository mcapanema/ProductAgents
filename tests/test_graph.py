from productagents.graph import build_graph
from productagents.schemas import (
    AnalystFindings,
    Evidence,
    Initiative,
    Recommendation,
)
from tests.fakes import FakeChatModel


def _model():
    return FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["finding"], signals=["signal"]),
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.75,
                rationale="evidence supports it",
                expected_outcomes=["growth"],
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
        "recommendation": None,
    }


async def test_graph_runs_both_analysts_then_strategist():
    graph = build_graph(_model())
    final = await graph.ainvoke(_initial_state())

    assert len(final["reports"]) == 2
    analysts = {r.analyst for r in final["reports"]}
    assert analysts == {"customer_research", "product_analytics"}
    assert final["recommendation"].recommendation == "Build it"
    assert final["recommendation"].confidence == 0.75
