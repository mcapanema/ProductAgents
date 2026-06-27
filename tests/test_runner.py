import logging
from dataclasses import dataclass

from productagents.agents.context import AgentContext
from productagents.agents.graph import build_graph
from productagents.agents.runner import (
    DebateTurnEvent,
    FinalVerdictEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    JudgmentEvent,
    NodeCompleteEvent,
    ProgressEvent,
    RecallEvent,
    RiskAssessmentEvent,
    run_decision,
)
from productagents.core.models import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    HumanDecision,
    Initiative,
    JudgeFinding,
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
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="ok",
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
    assert finished[0].recommendation is not None
    assert finished[0].governance is not None
    assert finished[0].recommendation.recommendation == "Build it"
    assert len(finished[0].reports) == 5
    assert len(finished[0].debate) == 4
    assert len(finished[0].risks) == 5
    assert finished[0].governance.verdict == "approve"
    judgments = [e for e in events if isinstance(e, JudgmentEvent)]
    assert len(judgments) == 1
    assert judgments[0].passed is True
    assert judgments[0].attempt == 1
    assert finished[0].judgment is not None
    assert finished[0].judgment.passed is True


@dataclass
class _FakeLearning:
    lessons: list[str]

    async def relevant_lessons(self, initiative):
        return self.lessons

    async def decisions(self):
        return []


async def test_run_decision_recalls_and_emits_lessons(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    initiative, evidence = _inputs()

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
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="ok",
            ),
            RiskFinding: RiskFinding(level="low", rationale="cheap"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="resources well spent"
            ),
        }
    )
    ctx = AgentContext(
        model=model,
        learning=_FakeLearning(["SSO integrations take longer than predicted"]),
    )
    graph = build_graph(ctx)

    events = [e async for e in run_decision(graph, initiative, evidence)]

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
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="ok",
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
    assert finished.governance is not None
    assert finished.governance.verdict == "reject"
    assert finished.governance.decided_by == "human"
    assert finished.governance.advisory_verdict == "approve"


async def test_run_decision_without_approver_auto_accepts_advisory(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = _hitl_graph()
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    finished = next(e for e in events if isinstance(e, FinishedEvent))
    assert finished.governance is not None
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
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="ok",
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
    assert finished.governance is not None
    # Governance degraded to verdict="error"; the no-approver fallback must coerce it.
    assert finished.governance.verdict == "approve"
    assert finished.governance.decided_by == "human"


async def test_runner_emits_node_error_when_analyst_degrades(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.agents.graph import build_graph
    from productagents.agents.runner import NodeErrorEvent, run_decision
    from productagents.core.models import (
        AnalystFindings,
        DebateArgument,
        Evidence,
        GovernanceFinding,
        Initiative,
        Recommendation,
        RiskFinding,
    )
    from productagents.core.models import JudgeFinding as _JudgeFinding
    from tests.fakes import FakeChatModel

    model = FakeChatModel(
        {
            AnalystFindings: RuntimeError("unexpected model error"),
            DebateArgument: DebateArgument(argument="a"),
            Recommendation: Recommendation(
                recommendation="r",
                confidence=0.5,
                rationale="x",
                expected_outcomes=["o"],
            ),
            _JudgeFinding: _JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="ok",
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
    assert any("unexpected model error" in e.message for e in errors)


async def _drive_with(model, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.agents.graph import build_graph
    from productagents.agents.runner import run_decision
    from productagents.core.models import Evidence, Initiative

    graph = build_graph(model)
    evidence = Evidence(scenario="s", customer_feedback="d", product_analytics={"x": 1})
    events = []
    async for event in run_decision(
        graph, Initiative(title="t", description="d"), evidence
    ):
        events.append(event)
    return events


def _base_results():
    from productagents.core.models import (
        AnalystFindings,
        DebateArgument,
        GovernanceFinding,
        JudgeFinding,
        Recommendation,
        RiskFinding,
    )

    return {
        AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
        DebateArgument: DebateArgument(argument="a"),
        Recommendation: Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=["o"]
        ),
        JudgeFinding: JudgeFinding(
            evidence_grounding_score=0.9,
            rationale_coherence_score=0.9,
            critique="ok",
        ),
        RiskFinding: RiskFinding(level="low", rationale="ok"),
        GovernanceFinding: GovernanceFinding(verdict="approve", rationale="ok"),
    }


async def test_runner_emits_node_error_for_debate(monkeypatch):
    from productagents.agents.runner import NodeErrorEvent
    from productagents.core.models import DebateArgument
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[DebateArgument] = RuntimeError("debate boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "debate" for e in events)


async def test_runner_emits_node_error_for_risk(monkeypatch):
    from productagents.agents.runner import NodeErrorEvent
    from productagents.core.models import RiskFinding
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[RiskFinding] = RuntimeError("risk boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "risk" for e in events)


async def test_runner_emits_node_error_for_strategist(monkeypatch):
    from productagents.agents.runner import NodeErrorEvent
    from productagents.core.models import Recommendation
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[Recommendation] = RuntimeError("strategist boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "strategist" for e in events)


async def test_runner_emits_node_error_for_governance(monkeypatch):
    from productagents.agents.runner import NodeErrorEvent
    from productagents.core.models import GovernanceFinding
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[GovernanceFinding] = RuntimeError("governance boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "governance" for e in events)


async def test_run_decision_aborts_on_fatal_chunk():
    from productagents.agents.runner import FinishedEvent, RunAbortedEvent, run_decision
    from productagents.core.models import Evidence, Initiative

    class _FatalGraph:
        async def astream(self, _input, _config, *, stream_mode):
            yield "custom", {"node": "customer_research", "status": "working…"}
            yield (
                "custom",
                {
                    "node": "customer_research",
                    "error": "Rate limit reached for the configured model. …",
                    "fatal": True,
                    "category": "rate_limit",
                },
            )
            # A real graph would keep emitting; the runner must stop before here.
            yield "custom", {"node": "market", "status": "should not be seen"}

    events = []
    async for event in run_decision(
        _FatalGraph(),
        Initiative(title="t", description="d"),
        Evidence(scenario="s", customer_feedback="d", product_analytics={}),
    ):
        events.append(event)

    aborted = [e for e in events if isinstance(e, RunAbortedEvent)]
    assert len(aborted) == 1
    assert aborted[0].category == "rate_limit"
    assert "Rate limit" in aborted[0].message
    # Fail-fast: no FinishedEvent, and the post-abort chunk was never processed.
    assert not any(isinstance(e, FinishedEvent) for e in events)
    assert all(getattr(e, "message", "") != "should not be seen" for e in events)


async def test_run_decision_aborts_end_to_end_on_rate_limit():
    from productagents.agents.graph import build_graph
    from productagents.agents.runner import FinishedEvent, RunAbortedEvent, run_decision
    from productagents.core.models import AnalystFindings, Evidence, Initiative
    from tests.fakes import FakeChatModel

    # Every analyst's structured call raises a rate-limit-shaped error.
    model = FakeChatModel(
        {AnalystFindings: RuntimeError("Rate limit exceeded: free-models-per-day")}
    )
    graph = build_graph(model)

    events = []
    async for event in run_decision(
        graph,
        Initiative(title="t", description="d"),
        Evidence(scenario="s", customer_feedback="d", product_analytics={}),
    ):
        events.append(event)

    assert any(
        isinstance(e, RunAbortedEvent) and e.category == "rate_limit" for e in events
    )
    assert not any(isinstance(e, FinishedEvent) for e in events)


async def test_run_decision_emits_recommendation_before_finished():
    from productagents.agents.runner import FinishedEvent, RecommendationEvent

    graph = _graph()
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    recs = [e for e in events if isinstance(e, RecommendationEvent)]
    assert recs, "expected at least one RecommendationEvent"
    assert recs[0].recommendation.recommendation == "Build it"

    # It must arrive before the terminal FinishedEvent so the panel renders live.
    rec_index = events.index(recs[0])
    finished_index = next(
        i for i, e in enumerate(events) if isinstance(e, FinishedEvent)
    )
    assert rec_index < finished_index


async def test_run_decision_emits_two_recommendation_events_on_judge_retry(monkeypatch):
    """When the judge fails once and passes on retry, two RecommendationEvents
    are emitted — one from the initial strategist run, one from the revision."""
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "1")
    # Set threshold high so the first JudgeFinding (low scores) fails the gate.
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_THRESHOLD", "0.7")

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
            # First judge call: both scores below threshold → fails; judge routes
            # back to strategist.  Second call: scores above threshold → passes.
            JudgeFinding: [
                JudgeFinding(
                    evidence_grounding_score=0.3,
                    rationale_coherence_score=0.3,
                    critique="needs more evidence",
                ),
                JudgeFinding(
                    evidence_grounding_score=0.9,
                    rationale_coherence_score=0.9,
                    critique="much better",
                ),
            ],
            RiskFinding: RiskFinding(level="low", rationale="cheap"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="resources well spent"
            ),
        }
    )
    graph = build_graph(model)
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    from productagents.agents.runner import RecommendationEvent

    recs = [e for e in events if isinstance(e, RecommendationEvent)]
    # First strategist run + one revision each emit a RecommendationEvent.
    assert len(recs) >= 2, (
        f"expected at least 2 RecommendationEvents on judge retry, got {len(recs)}"
    )

    # Judge should have made two attempts: first failed, second passed.
    judgments = [e for e in events if isinstance(e, JudgmentEvent)]
    assert len(judgments) == 2
    assert judgments[0].passed is False
    assert judgments[1].passed is True

    finished = next(e for e in events if isinstance(e, FinishedEvent))
    assert finished.judgment is not None
    assert finished.judgment.passed is True


async def test_run_decision_warns_on_unhandled_custom_chunk(caplog):
    import logging

    from productagents.agents.runner import FinishedEvent, ProgressEvent, run_decision
    from productagents.core.models import Evidence, Initiative

    class _MysteryGraph:
        async def astream(self, _input, _config, *, stream_mode):
            # A chunk whose only payload key is unknown: previously this became an
            # empty ProgressEvent (silently dropped); now it must be logged, not
            # turned into a bogus event.
            yield "custom", {"node": "mystery", "surprise": {"x": 1}}

    with caplog.at_level(logging.WARNING, logger="productagents.agents.runner"):
        events = [
            e
            async for e in run_decision(
                _MysteryGraph(),
                Initiative(title="t", description="d"),
                Evidence(scenario="s", customer_feedback="d", product_analytics={}),
            )
        ]

    # No bogus event was synthesized for the unknown chunk...
    assert not any(isinstance(e, ProgressEvent) and e.node == "mystery" for e in events)
    # ...and the drop was surfaced in the log.
    assert any("unhandled custom chunk" in r.message for r in caplog.records)
    # The run still finishes cleanly (the unknown chunk is skipped, not fatal).
    assert any(isinstance(e, FinishedEvent) for e in events)


async def test_run_decision_logs_a_decision_run_span(caplog):
    graph = _graph()
    initiative, evidence = _inputs()
    with caplog.at_level(logging.INFO, logger="productagents.observability"):
        async for _ in run_decision(graph, initiative, evidence):
            pass
    run_lines = [
        rec.getMessage()
        for rec in caplog.records
        if rec.getMessage().startswith("decision.run ")
    ]
    assert len(run_lines) == 1
    assert "duration_ms=" in run_lines[0]
    assert "status=ok" in run_lines[0]
    assert "reports=" in run_lines[0]


async def test_run_decision_still_emits_progress_for_status_chunks():
    from productagents.agents.runner import FinishedEvent, ProgressEvent, run_decision
    from productagents.core.models import Evidence, Initiative

    class _StatusGraph:
        async def astream(self, _input, _config, *, stream_mode):
            yield "custom", {"node": "customer_research", "status": "working…"}

    events = [
        e
        async for e in run_decision(
            _StatusGraph(),
            Initiative(title="t", description="d"),
            Evidence(scenario="s", customer_feedback="d", product_analytics={}),
        )
    ]
    progress = [e for e in events if isinstance(e, ProgressEvent)]
    assert any(
        p.node == "customer_research" and p.message == "working…" for p in progress
    )
    assert any(isinstance(e, FinishedEvent) for e in events)
