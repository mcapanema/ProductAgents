"""Normalize LangGraph's streamed chunks into plain UI-facing events."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from productagents.schemas import AnalystReport, Evidence, Initiative, Recommendation


@dataclass
class ProgressEvent:
    node: str
    message: str


@dataclass
class NodeCompleteEvent:
    node: str
    report: AnalystReport


@dataclass
class FinishedEvent:
    recommendation: Recommendation | None
    reports: list[AnalystReport]


async def run_decision(
    graph, initiative: Initiative, evidence: Evidence
) -> AsyncIterator[ProgressEvent | NodeCompleteEvent | FinishedEvent]:
    """Stream a decision run, yielding normalized events.

    Consumes `graph.astream(..., stream_mode=["updates", "custom"])`, where each
    streamed item is a `(mode, chunk)` tuple: `custom` chunks are the dicts
    emitted by nodes via `get_stream_writer()`, and `updates` chunks map a node
    name to the partial state it returned.
    """
    initial_state = {
        "initiative": initiative,
        "evidence": evidence,
        "reports": [],
        "recommendation": None,
    }
    collected_reports: list[AnalystReport] = []
    recommendation: Recommendation | None = None

    async for mode, chunk in graph.astream(
        initial_state, stream_mode=["updates", "custom"]
    ):
        if mode == "custom":
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
                if node_state.get("recommendation") is not None:
                    recommendation = node_state["recommendation"]

    yield FinishedEvent(recommendation=recommendation, reports=collected_reports)
