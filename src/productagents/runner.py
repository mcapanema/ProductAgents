"""Normalize LangGraph's streamed chunks into plain UI-facing events."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Evidence,
    Initiative,
    Recommendation,
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
class FinishedEvent:
    recommendation: Recommendation | None
    reports: list[AnalystReport]
    debate: list[DebateTurn]


async def run_decision(
    graph, initiative: Initiative, evidence: Evidence
) -> AsyncIterator[ProgressEvent | NodeCompleteEvent | DebateTurnEvent | FinishedEvent]:
    """Stream a decision run, yielding normalized events.

    Consumes `graph.astream(..., stream_mode=["updates", "custom"])`. Each item is
    a `(mode, chunk)` tuple. `custom` chunks carry either a debate `turn` dict or a
    progress `status`; `updates` chunks map a node name to the partial state it
    returned.
    """
    initial_state = {
        "initiative": initiative,
        "evidence": evidence,
        "reports": [],
        "debate": [],
        "recommendation": None,
    }
    collected_reports: list[AnalystReport] = []
    collected_debate: list[DebateTurn] = []
    recommendation: Recommendation | None = None

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
                if node_state.get("recommendation") is not None:
                    recommendation = node_state["recommendation"]

    yield FinishedEvent(
        recommendation=recommendation,
        reports=collected_reports,
        debate=collected_debate,
    )
