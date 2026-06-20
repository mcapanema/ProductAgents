from productagents.graph import build_graph
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    Initiative,
    Recommendation,
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
    }


async def test_graph_runs_analysts_then_debate_then_strategist(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    graph = build_graph(_model())
    final = await graph.ainvoke(_initial_state())

    assert len(final["reports"]) == 2
    analysts = {r.analyst for r in final["reports"]}
    assert analysts == {"customer_research", "product_analytics"}

    assert [(t.round, t.side) for t in final["debate"]] == [
        (1, "advocate"),
        (1, "skeptic"),
        (2, "advocate"),
        (2, "skeptic"),
    ]

    assert final["recommendation"].recommendation == "Build it"
