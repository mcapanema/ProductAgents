from productagents.graph import build_graph
from productagents.runner import (
    DebateTurnEvent,
    FinalVerdictEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    NodeCompleteEvent,
    ProgressEvent,
    RecallEvent,
    RiskAssessmentEvent,
    run_decision,
)
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    DecisionRecord,
    Evidence,
    GovernanceFinding,
    HumanDecision,
    Initiative,
    OutcomeRecord,
    Recommendation,
    RiskFinding,
)
from tests.fakes import FakeChatModel


def _graph():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            ),
            RiskFinding: RiskFinding(level="low", rationale="cheap"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="resources well spent"
            ),
        }
    )
    return build_graph(model)


def _inputs():
    return (
        Initiative(title="Add SSO", description="Enterprise SSO"),
        Evidence(scenario="sample", customer_feedback="d", product_analytics={"x": 1}),
    )


async def test_run_decision_emits_all_event_types(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    graph = _graph()
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    progress = [e for e in events if isinstance(e, ProgressEvent)]
    completions = [e for e in events if isinstance(e, NodeCompleteEvent)]
    debate_turns = [e for e in events if isinstance(e, DebateTurnEvent)]
    risk_events = [e for e in events if isinstance(e, RiskAssessmentEvent)]
    governance_events = [e for e in events if isinstance(e, GovernanceVerdictEvent)]
    finished = [e for e in events if isinstance(e, FinishedEvent)]

    assert progress  # at least one in-node progress update
    assert {c.report.analyst for c in completions} == {
        "customer_research",
        "product_analytics",
        "market",
        "business",
        "technical",
    }
    assert [(t.round, t.side) for t in debate_turns] == [
        (1, "advocate"),
        (1, "skeptic"),
        (2, "advocate"),
        (2, "skeptic"),
    ]
    assert [r.reviewer for r in risk_events] == [
        "delivery",
        "adoption",
        "strategic",
        "financial",
        "organizational",
    ]
    assert [g.verdict for g in governance_events] == ["approve"]
    assert len(finished) == 1
    assert finished[0].recommendation.recommendation == "Build it"
    assert len(finished[0].reports) == 5
    assert len(finished[0].debate) == 4
    assert len(finished[0].risks) == 5
    assert finished[0].governance.verdict == "approve"


async def test_run_decision_recalls_and_emits_lessons(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = _graph()
    initiative, evidence = _inputs()

    prior = DecisionRecord(
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

    events = [
        e
        async for e in run_decision(
            graph, initiative, evidence, portfolio=[prior], outcomes=[outcome]
        )
    ]

    recalls = [e for e in events if isinstance(e, RecallEvent)]
    finished = [e for e in events if isinstance(e, FinishedEvent)]

    assert len(recalls) == 1
    assert any("take longer than predicted" in line for line in recalls[0].lessons)
    assert any(
        "take longer than predicted" in line for line in finished[0].prior_lessons
    )


def _hitl_graph():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            ),
            RiskFinding: RiskFinding(level="low", rationale="cheap"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="resources well spent"
            ),
        }
    )
    return build_graph(model, human_in_the_loop=True)


async def test_run_decision_human_override_becomes_final_verdict(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = _hitl_graph()
    initiative, evidence = _inputs()
    seen_advisory = []

    async def approver(advisory):
        seen_advisory.append(advisory)
        return HumanDecision(verdict="reject", rationale="no capacity")

    events = [
        e async for e in run_decision(graph, initiative, evidence, approver=approver)
    ]

    # The approver was shown the AI's advisory verdict.
    assert len(seen_advisory) == 1
    assert seen_advisory[0].verdict == "approve"

    finals = [e for e in events if isinstance(e, FinalVerdictEvent)]
    assert len(finals) == 1
    assert finals[0].verdict == "reject"
    assert finals[0].decided_by == "human"

    finished = next(e for e in events if isinstance(e, FinishedEvent))
    assert finished.governance.verdict == "reject"
    assert finished.governance.decided_by == "human"
    assert finished.governance.advisory_verdict == "approve"


async def test_run_decision_without_approver_auto_accepts_advisory(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = _hitl_graph()
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    finished = next(e for e in events if isinstance(e, FinishedEvent))
    assert finished.governance.verdict == "approve"


def _hitl_graph_degraded_governance():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            ),
            RiskFinding: RiskFinding(level="low", rationale="cheap"),
            GovernanceFinding: RuntimeError("governance LLM down"),
        }
    )
    return build_graph(model, human_in_the_loop=True)


async def test_run_decision_without_approver_coerces_degraded_advisory_to_approve(
    monkeypatch,
):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = _hitl_graph_degraded_governance()
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    finished = next(e for e in events if isinstance(e, FinishedEvent))
    # Governance degraded to verdict="error"; the no-approver fallback must coerce it.
    assert finished.governance.verdict == "approve"
    assert finished.governance.decided_by == "human"


async def test_runner_emits_node_error_when_analyst_degrades(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.graph import build_graph
    from productagents.runner import NodeErrorEvent, run_decision
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

    model = FakeChatModel(
        {
            AnalystFindings: RuntimeError("429 Too Many Requests: rate limit reached"),
            DebateArgument: DebateArgument(argument="a"),
            Recommendation: Recommendation(
                recommendation="r",
                confidence=0.5,
                rationale="x",
                expected_outcomes=["o"],
            ),
            RiskFinding: RiskFinding(level="low", rationale="ok"),
            GovernanceFinding: GovernanceFinding(verdict="approve", rationale="ok"),
        }
    )
    graph = build_graph(model)
    evidence = Evidence(scenario="s", customer_feedback="d", product_analytics={"x": 1})

    events = []
    async for event in run_decision(
        graph, Initiative(title="t", description="d"), evidence
    ):
        events.append(event)

    errors = [e for e in events if isinstance(e, NodeErrorEvent)]
    analyst_ids = {
        "customer_research",
        "product_analytics",
        "market",
        "business",
        "technical",
    }
    assert errors, "expected NodeErrorEvent(s) for the failing analysts"
    assert all(e.node in analyst_ids for e in errors)
    assert any("429" in e.message for e in errors)


async def _drive_with(model, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.graph import build_graph
    from productagents.runner import run_decision
    from productagents.schemas import Evidence, Initiative

    graph = build_graph(model)
    evidence = Evidence(scenario="s", customer_feedback="d", product_analytics={"x": 1})
    events = []
    async for event in run_decision(
        graph, Initiative(title="t", description="d"), evidence
    ):
        events.append(event)
    return events


def _base_results():
    from productagents.schemas import (
        AnalystFindings,
        DebateArgument,
        GovernanceFinding,
        Recommendation,
        RiskFinding,
    )

    return {
        AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
        DebateArgument: DebateArgument(argument="a"),
        Recommendation: Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=["o"]
        ),
        RiskFinding: RiskFinding(level="low", rationale="ok"),
        GovernanceFinding: GovernanceFinding(verdict="approve", rationale="ok"),
    }


async def test_runner_emits_node_error_for_debate(monkeypatch):
    from productagents.runner import NodeErrorEvent
    from productagents.schemas import DebateArgument
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[DebateArgument] = RuntimeError("debate boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "debate" for e in events)


async def test_runner_emits_node_error_for_risk(monkeypatch):
    from productagents.runner import NodeErrorEvent
    from productagents.schemas import RiskFinding
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[RiskFinding] = RuntimeError("risk boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "risk" for e in events)


async def test_runner_emits_node_error_for_strategist(monkeypatch):
    from productagents.runner import NodeErrorEvent
    from productagents.schemas import Recommendation
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[Recommendation] = RuntimeError("strategist boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "strategist" for e in events)


async def test_runner_emits_node_error_for_governance(monkeypatch):
    from productagents.runner import NodeErrorEvent
    from productagents.schemas import GovernanceFinding
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[GovernanceFinding] = RuntimeError("governance boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "governance" for e in events)
