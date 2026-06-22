"""Normalize LangGraph's streamed chunks into plain UI-facing events."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import uuid4

from langgraph.types import Command

from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    DecisionRecord,
    Evidence,
    GovernanceVerdict,
    HumanDecision,
    Initiative,
    JudgeVerdict,
    OutcomeRecord,
    Recommendation,
    RiskAssessment,
)


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


@dataclass(frozen=True)
class NodeErrorEvent:
    node: str
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
    ("turn", _build_debate_turn),
    ("assessment", _build_risk_assessment),
    ("final_verdict", _build_final_verdict),
    ("judgment", _build_judgment),
    ("verdict", _build_governance_verdict),
)


async def run_decision(
    graph,
    initiative: Initiative,
    evidence: Evidence,
    portfolio: list[DecisionRecord] | None = None,
    outcomes: list[OutcomeRecord] | None = None,
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
    | FinalVerdictEvent
    | RecallEvent
    | FinishedEvent
]:
    """Stream a decision run, yielding normalized events.

    Consumes `graph.astream(..., stream_mode=["updates", "custom"])`. Each item is
    a `(mode, chunk)` tuple. `custom` chunks carry a debate `turn` dict, a risk
    `assessment` dict, a governance `verdict` dict, a governance `final_verdict` dict
    after human approval, or a progress `status`; `updates` chunks map a node name to
    the partial state it returned. Recent prior decisions are passed in as `portfolio`
    and seeded into graph state for the governance node. An `__interrupt__` update
    pauses the run until the injected `approver` returns a `HumanDecision`, which
    resumes the graph via `Command(resume=...)`.
    """
    initial_state = {
        "initiative": initiative,
        "evidence": evidence,
        "reports": [],
        "debate": [],
        "recommendation": None,
        "risks": [],
        "portfolio": portfolio or [],
        "outcomes": outcomes or [],
        "prior_lessons": [],
        "governance": None,
        "judgment": None,
        "judge_attempts": 0,
    }
    collected_reports: list[AnalystReport] = []
    collected_debate: list[DebateTurn] = []
    collected_risks: list[RiskAssessment] = []
    collected_lessons: list[str] = []
    recommendation: Recommendation | None = None
    governance: GovernanceVerdict | None = None
    judgment: JudgeVerdict | None = None

    config = {"configurable": {"thread_id": uuid4().hex}}
    stream_input: dict | Command = initial_state

    while True:
        pending_interrupt: dict | None = None
        async for mode, chunk in graph.astream(
            stream_input, config, stream_mode=["updates", "custom"]
        ):
            if mode == "custom":
                for key, builder in _CUSTOM_BUILDERS:
                    if key in chunk:
                        yield builder(chunk)
                        break
                else:
                    if "error" in chunk:
                        yield NodeErrorEvent(
                            node=chunk.get("node", ""), message=chunk["error"]
                        )
                    else:
                        yield ProgressEvent(
                            node=chunk.get("node", ""), message=chunk.get("status", "")
                        )
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
                    if node_state.get("debate"):
                        collected_debate = node_state["debate"]
                    if node_state.get("risks"):
                        collected_risks = node_state["risks"]
                    if "prior_lessons" in node_state:
                        collected_lessons = node_state["prior_lessons"]
                        yield RecallEvent(lessons=collected_lessons)
                    if node_state.get("recommendation") is not None:
                        recommendation = node_state["recommendation"]
                    if node_state.get("governance") is not None:
                        governance = node_state["governance"]
                    if node_state.get("judgment") is not None:
                        judgment = node_state["judgment"]

        if pending_interrupt is None:
            break

        advisory_dump = pending_interrupt.get("advisory")
        advisory = GovernanceVerdict(**advisory_dump) if advisory_dump else None
        if approver is not None:
            decision = await approver(advisory)
        else:
            advisory_verdict = (
                advisory.verdict
                if advisory and advisory.verdict != "error"
                else "approve"
            )
            decision = HumanDecision(
                verdict=advisory_verdict,
                rationale=advisory.rationale if advisory else "",
            )
        stream_input = Command(resume=decision.model_dump())

    yield FinishedEvent(
        recommendation=recommendation,
        reports=collected_reports,
        debate=collected_debate,
        risks=collected_risks,
        governance=governance,
        prior_lessons=collected_lessons,
        judgment=judgment,
    )
