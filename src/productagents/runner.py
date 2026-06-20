"""Normalize LangGraph's streamed chunks into plain UI-facing events."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    DecisionRecord,
    Evidence,
    GovernanceVerdict,
    Initiative,
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
class FinishedEvent:
    recommendation: Recommendation | None
    reports: list[AnalystReport]
    debate: list[DebateTurn]
    risks: list[RiskAssessment]
    governance: GovernanceVerdict | None


async def run_decision(
    graph,
    initiative: Initiative,
    evidence: Evidence,
    portfolio: list[DecisionRecord] | None = None,
) -> AsyncIterator[
    ProgressEvent
    | NodeCompleteEvent
    | DebateTurnEvent
    | RiskAssessmentEvent
    | GovernanceVerdictEvent
    | FinishedEvent
]:
    """Stream a decision run, yielding normalized events.

    Consumes `graph.astream(..., stream_mode=["updates", "custom"])`. Each item is
    a `(mode, chunk)` tuple. `custom` chunks carry a debate `turn` dict, a risk
    `assessment` dict, a governance `verdict` dict, or a progress `status`;
    `updates` chunks map a node name to the partial state it returned. Recent
    prior decisions are passed in as `portfolio` and seeded into graph state for
    the governance node.
    """
    initial_state = {
        "initiative": initiative,
        "evidence": evidence,
        "reports": [],
        "debate": [],
        "recommendation": None,
        "risks": [],
        "portfolio": portfolio or [],
        "outcomes": [],
        "prior_lessons": [],
        "governance": None,
    }
    collected_reports: list[AnalystReport] = []
    collected_debate: list[DebateTurn] = []
    collected_risks: list[RiskAssessment] = []
    recommendation: Recommendation | None = None
    governance: GovernanceVerdict | None = None

    async for mode, chunk in graph.astream(
        initial_state, stream_mode=["updates", "custom"]
    ):
        if mode == "custom":
            if "turn" in chunk:
                turn = chunk["turn"]
                yield DebateTurnEvent(
                    round=turn["round"],
                    side=turn["side"],
                    argument=turn["argument"],
                )
            elif "assessment" in chunk:
                a = chunk["assessment"]
                yield RiskAssessmentEvent(
                    reviewer=a["reviewer"],
                    role=a["role"],
                    level=a["level"],
                    rationale=a["rationale"],
                )
            elif "verdict" in chunk:
                v = chunk["verdict"]
                yield GovernanceVerdictEvent(
                    verdict=v["verdict"],
                    rationale=v["rationale"],
                )
            else:
                yield ProgressEvent(
                    node=chunk.get("node", ""), message=chunk.get("status", "")
                )
        elif mode == "updates":
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
                if node_state.get("recommendation") is not None:
                    recommendation = node_state["recommendation"]
                if node_state.get("governance") is not None:
                    governance = node_state["governance"]

    yield FinishedEvent(
        recommendation=recommendation,
        reports=collected_reports,
        debate=collected_debate,
        risks=collected_risks,
        governance=governance,
    )
