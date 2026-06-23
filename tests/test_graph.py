import pytest
from productagents.core.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    Initiative,
    JudgeFinding,
    Recommendation,
    RiskFinding,
)

from productagents.graph import build_graph
from productagents.runner import (
    FinishedEvent,
    GovernanceVerdictEvent,
    JudgmentEvent,
    RiskAssessmentEvent,
    run_decision,
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
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="well grounded and coherent",
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
        "outcomes": [],
        "prior_lessons": [],
        "governance": None,
        "judgment": None,
        "judge_attempts": 0,
    }


def test_default_graph_has_no_human_approval_node():
    graph = build_graph(_model())
    assert "human_approval" not in graph.nodes


def test_human_in_the_loop_graph_adds_human_approval_node():
    graph = build_graph(_model(), human_in_the_loop=True)
    assert "human_approval" in graph.nodes


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

    assert final["prior_lessons"] == []


def _failing_judge_model():
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
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.1,
                rationale_coherence_score=0.1,
                critique="ungrounded and incoherent",
            ),
            RiskFinding: RiskFinding(level="medium", rationale="manageable risk"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="best use of resources"
            ),
        }
    )


async def test_graph_judge_passes_without_retry(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = build_graph(_model())
    final = await graph.ainvoke(_initial_state())
    assert final["judgment"].passed is True
    assert final["judge_attempts"] == 1  # judged once, no loop
    assert final["governance"].verdict == "approve"


async def test_graph_judge_retries_then_proceeds(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    monkeypatch.delenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", raising=False)  # default 1
    graph = build_graph(_failing_judge_model())
    final = await graph.ainvoke(_initial_state())
    # Default 1 retry: strategist runs twice, so the judge runs twice.
    assert final["judge_attempts"] == 2
    assert final["judgment"].passed is False
    # The pipeline still completed past the gate.
    assert len(final["risks"]) == 5
    assert final["governance"].verdict == "approve"


async def test_graph_judge_score_only_when_retries_zero(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "0")
    graph = build_graph(_failing_judge_model())
    final = await graph.ainvoke(_initial_state())
    assert final["judge_attempts"] == 1  # scored once, never looped
    assert final["judgment"].passed is False
    assert final["governance"].verdict == "approve"


@pytest.fixture
def _failed_strategist_model():
    return FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: RuntimeError("Provider returned error"),
        }
    )


async def test_failed_recommendation_ends_run_before_governance(
    _failed_strategist_model,  # noqa: PT019
    monkeypatch,
):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = build_graph(_failed_strategist_model, human_in_the_loop=True)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    initiative = Initiative(title="SSO", description="SSO")

    events = [e async for e in run_decision(graph, initiative, evidence)]

    # No judge, risk, or governance events: the run fails fast at the strategist.
    assert not any(isinstance(e, JudgmentEvent) for e in events)
    assert not any(isinstance(e, RiskAssessmentEvent) for e in events)
    assert not any(isinstance(e, GovernanceVerdictEvent) for e in events)
    finished = next(e for e in events if isinstance(e, FinishedEvent))
    assert finished.recommendation is not None
    assert finished.recommendation.failed is True
    assert finished.governance is None
