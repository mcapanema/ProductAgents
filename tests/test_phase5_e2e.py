"""End-to-end: connector-shaped write → customer_research reads it → decision runs."""

from productagents.agents.context import AgentContext
from productagents.agents.graph import build_graph
from productagents.agents.runner import FinishedEvent, NodeCompleteEvent, run_decision
from productagents.core.models import (
    AnalystFindings,
    CustomerFeedback,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    Initiative,
    JudgeFinding,
    Recommendation,
    RiskFinding,
)
from productagents.knowledge import DbCanonicalSink, build_services
from tests.fakes import FakeChatModel
from tests.storage_fixtures import memory_store


def _full_graph_model():
    """FakeChatModel mapping every structured-output schema the graph calls.

    Matches the schema map in tests/test_graph.py exactly.
    """
    return FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["demand"], signals=["sig"]),
            DebateArgument: DebateArgument(argument="point"),
            Recommendation: Recommendation(
                recommendation="Ship SSO",
                confidence=0.8,
                rationale="strong demand",
                expected_outcomes=["more enterprise wins"],
            ),
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="solid",
            ),
            RiskFinding: RiskFinding(level="low", rationale="ok"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="aligned"
            ),
        }
    )


def _evidence():
    return Evidence(
        scenario="sample",
        customer_feedback="SCENARIO fallback only",
        product_analytics={},
    )


async def test_synced_feedback_reaches_a_decision_run():
    async with memory_store() as (sm, _engine):
        await DbCanonicalSink(sm).write(
            CustomerFeedback(body="STORE: enterprises need SSO now")
        )
        async with sm() as session:
            services = build_services(session)
            ctx = AgentContext(model=_full_graph_model(), feedback=services.feedback)
            graph = build_graph(ctx)

            cr_done = False
            finished = None
            async for event in run_decision(
                graph, Initiative(title="SSO", description="SSO"), _evidence()
            ):
                if (
                    isinstance(event, NodeCompleteEvent)
                    and event.node == "customer_research"
                ):
                    cr_done = True
                if isinstance(event, FinishedEvent):
                    finished = event

    assert cr_done
    assert finished is not None
    rec = finished.recommendation
    assert rec is not None
    assert rec.recommendation == "Ship SSO"
