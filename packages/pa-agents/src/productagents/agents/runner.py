"""Normalize LangGraph's streamed chunks into plain UI-facing events."""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import uuid4

from langgraph.types import Command

from productagents.agents import stream_events as ev
from productagents.agents.graph import ANALYST_IDS
from productagents.core.models import (
    AnalystReport,
    DebateTurn,
    Evidence,
    GovernanceVerdict,
    Initiative,
    JudgeVerdict,
    Recommendation,
    RiskAssessment,
)
from productagents.core.observability import span

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    node: str
    message: str


@dataclass
class NodeCompleteEvent:
    node: str
    report: AnalystReport


@dataclass
class DebateTurnEvent:
    round: int
    side: str
    argument: str


@dataclass
class RiskAssessmentEvent:
    reviewer: str
    role: str
    level: str
    rationale: str


@dataclass
class GovernanceVerdictEvent:
    verdict: str
    rationale: str


@dataclass
class JudgmentEvent:
    evidence_grounding_score: float
    rationale_coherence_score: float
    passed: bool
    critique: str
    attempt: int


@dataclass
class RecommendationEvent:
    recommendation: Recommendation


@dataclass(frozen=True)
class NodeErrorEvent:
    node: str
    message: str


@dataclass(frozen=True)
class RunAbortedEvent:
    node: str
    category: str
    message: str


@dataclass
class FinalVerdictEvent:
    verdict: str
    rationale: str
    decided_by: str


@dataclass
class RecallEvent:
    lessons: list[str]


@dataclass
class FinishedEvent:
    recommendation: Recommendation | None
    reports: list[AnalystReport]
    debate: list[DebateTurn]
    risks: list[RiskAssessment]
    governance: GovernanceVerdict | None
    prior_lessons: list[str] = field(default_factory=list)
    judgment: JudgeVerdict | None = None


def _build_debate_turn(chunk: dict) -> DebateTurnEvent:
    turn = chunk["turn"]
    return DebateTurnEvent(
        round=turn["round"], side=turn["side"], argument=turn["argument"]
    )


def _build_risk_assessment(chunk: dict) -> RiskAssessmentEvent:
    a = chunk["assessment"]
    return RiskAssessmentEvent(
        reviewer=a["reviewer"],
        role=a["role"],
        level=a["level"],
        rationale=a["rationale"],
    )


def _build_final_verdict(chunk: dict) -> FinalVerdictEvent:
    fv = chunk["final_verdict"]
    return FinalVerdictEvent(
        verdict=fv["verdict"], rationale=fv["rationale"], decided_by=fv["decided_by"]
    )


def _build_judgment(chunk: dict) -> JudgmentEvent:
    j = chunk["judgment"]
    return JudgmentEvent(
        evidence_grounding_score=j["evidence_grounding_score"],
        rationale_coherence_score=j["rationale_coherence_score"],
        passed=j["passed"],
        critique=j["critique"],
        attempt=j["attempt"],
    )


def _build_governance_verdict(chunk: dict) -> GovernanceVerdictEvent:
    v = chunk["verdict"]
    return GovernanceVerdictEvent(verdict=v["verdict"], rationale=v["rationale"])


# Ordered so the first matching key wins, mirroring the original elif chain.
_CUSTOM_BUILDERS = (
    (ev.TURN, _build_debate_turn),
    (ev.ASSESSMENT, _build_risk_assessment),
    (ev.FINAL_VERDICT, _build_final_verdict),
    (ev.JUDGMENT, _build_judgment),
    (ev.VERDICT, _build_governance_verdict),
)


def _event_from_custom(chunk: dict):
    """Translate one `custom`-mode chunk into a UI event, or `None` if unknown.

    A `None` return means the chunk matched no known shape — the caller logs it
    rather than synthesizing a bogus event (the old silent-drop footgun).
    """
    for key, builder in _CUSTOM_BUILDERS:
        if key in chunk:
            return builder(chunk)
    if ev.ERROR in chunk:
        if chunk.get(ev.FATAL):
            return RunAbortedEvent(
                node=chunk.get(ev.NODE, ""),
                category=chunk.get(ev.CATEGORY, "unknown"),
                message=chunk[ev.ERROR],
            )
        return NodeErrorEvent(node=chunk.get(ev.NODE, ""), message=chunk[ev.ERROR])
    if ev.STATUS in chunk:
        return ProgressEvent(node=chunk.get(ev.NODE, ""), message=chunk[ev.STATUS])
    return None


def _all_analysts_failed(reports: list[AnalystReport]) -> bool:
    """True once every analyst has reported and all of them degraded.

    Guards against persisting an all-placeholder DecisionRecord when the whole
    provider is down but each failure was non-fatal (per-node UPSTREAM/UNKNOWN),
    so no `emit_fatal` marker ever fired. Only analyst nodes contribute to
    `reports`, so `recall`/`governance` failures never trip this.
    """
    reported = {r.analyst for r in reports}
    return reported == ANALYST_IDS and all(r.failed for r in reports)


def _build_initial_state(
    initiative: Initiative | None, evidence: Evidence | None
) -> dict[str, object]:
    """Build the graph's initial state dict.

    Field set mirrors `GraphState` in `graph.py` — see `initial_state_keys()`
    and `tests/test_graph_state_shape.py`, which guards against the two
    silently drifting apart.
    """
    return {
        "initiative": initiative,
        "evidence": evidence,
        "reports": [],
        "debate": [],
        "recommendation": None,
        "risks": [],
        "prior_lessons": [],
        "governance": None,
        "judgment": None,
        "judge_attempts": 0,
    }


def initial_state_keys() -> frozenset[str]:
    """Key set of the graph's initial state, importable without a graph run."""
    return frozenset(_build_initial_state(None, None))


async def run_decision(
    graph,
    initiative: Initiative,
    evidence: Evidence,
    *,
    approver=None,
) -> AsyncIterator[
    ProgressEvent
    | NodeCompleteEvent
    | DebateTurnEvent
    | RiskAssessmentEvent
    | GovernanceVerdictEvent
    | JudgmentEvent
    | NodeErrorEvent
    | RunAbortedEvent
    | FinalVerdictEvent
    | RecallEvent
    | RecommendationEvent
    | FinishedEvent
]:
    """Stream a decision run, yielding normalized events.

    Consumes `graph.astream(..., stream_mode=["updates", "custom"])`. Each item is
    a `(mode, chunk)` tuple. `custom` chunks carry a debate `turn` dict, a risk
    `assessment` dict, a governance `verdict` dict, a governance `final_verdict` dict
    after human approval, or a progress `status`; `updates` chunks map a node name to
    the partial state it returned. Lessons from past decisions are retrieved inside the
    graph by the recall node via the LearningService wired into the AgentContext. An
    `__interrupt__` update pauses the run until the injected `approver` returns a
    `HumanDecision`, which resumes the graph via `Command(resume=...)`. If no
    `approver` was configured, the run aborts with a `RunAbortedEvent` instead
    of silently auto-approving.
    """
    initial_state = _build_initial_state(initiative, evidence)
    collected_reports: list[AnalystReport] = []
    collected_debate: list[DebateTurn] = []
    collected_risks: list[RiskAssessment] = []
    collected_lessons: list[str] = []
    recommendation: Recommendation | None = None
    governance: GovernanceVerdict | None = None
    judgment: JudgeVerdict | None = None

    config = {"configurable": {"thread_id": uuid4().hex}}
    stream_input: dict | Command = initial_state

    # ponytail: one flat span per run — "one trace = one decision". An early
    # consumer break closes the generator (GeneratorExit) and logs status=error,
    # which is fine/rare. Per-node breakdown comes from graph.py's decision.<node>.
    with span("decision.run", initiative=initiative.title) as trace:
        while True:
            pending_interrupt: dict | None = None
            async for mode, chunk in graph.astream(
                stream_input, config, stream_mode=["updates", "custom"]
            ):
                if mode == "custom":
                    event = _event_from_custom(chunk)
                    if event is None:
                        logger.warning(
                            "runner: unhandled custom chunk keys=%s", sorted(chunk)
                        )
                    elif isinstance(event, RunAbortedEvent):
                        trace["aborted"] = True
                        yield event
                        return
                    else:
                        yield event
                elif mode == "updates":
                    if "__interrupt__" in chunk:
                        pending_interrupt = chunk["__interrupt__"][0].value
                        continue
                    for node_name, node_state in chunk.items():
                        if not node_state:
                            continue
                        for report in node_state.get("reports", []) or []:
                            collected_reports.append(report)
                            yield NodeCompleteEvent(node=node_name, report=report)
                            if _all_analysts_failed(collected_reports):
                                trace["aborted"] = True
                                yield RunAbortedEvent(
                                    node=node_name,
                                    category="all_analysts_failed",
                                    message=(
                                        "every analyst failed to produce findings — "
                                        "aborting rather than persisting an "
                                        "all-placeholder decision"
                                    ),
                                )
                                return
                        if node_state.get("debate"):
                            collected_debate = node_state["debate"]
                        if node_state.get("risks"):
                            collected_risks = node_state["risks"]
                        if "prior_lessons" in node_state:
                            collected_lessons = node_state["prior_lessons"]
                            yield RecallEvent(lessons=collected_lessons)
                        if node_state.get("recommendation") is not None:
                            recommendation = node_state["recommendation"]
                            yield RecommendationEvent(recommendation=recommendation)
                        if node_state.get("governance") is not None:
                            governance = node_state["governance"]
                        if node_state.get("judgment") is not None:
                            judgment = node_state["judgment"]

            if pending_interrupt is None:
                break

            advisory_dump = pending_interrupt.get("advisory")
            advisory = GovernanceVerdict(**advisory_dump) if advisory_dump else None
            if approver is None:
                trace["aborted"] = True
                yield RunAbortedEvent(
                    node="human_approval",
                    category="missing_approver",
                    message=(
                        "run paused for human approval but no approver was "
                        "configured — aborting rather than auto-approving"
                    ),
                )
                return
            decision = await approver(advisory)
            stream_input = Command(resume=decision.model_dump())

        trace["reports"] = len(collected_reports)
        trace["verdict"] = governance.verdict if governance else "none"
        yield FinishedEvent(
            recommendation=recommendation,
            reports=collected_reports,
            debate=collected_debate,
            risks=collected_risks,
            governance=governance,
            prior_lessons=collected_lessons,
            judgment=judgment,
        )
