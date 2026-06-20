"""Product Strategist node: synthesizes analyst reports and the debate."""

from productagents.agents._stream import get_writer
from productagents.schemas import AnalystReport, DebateTurn, Initiative, Recommendation

NODE_ID = "strategist"


def _format_reports(reports: list[AnalystReport]) -> str:
    blocks = []
    for report in reports:
        status = " (FAILED — no input)" if report.failed else ""
        blocks.append(
            f"## {report.role}{status}\n"
            f"Findings: {report.findings}\n"
            f"Signals: {report.signals}\n"
        )
    return "\n".join(blocks)


def _format_debate(turns: list[DebateTurn]) -> str:
    if not turns:
        return "(no debate)"
    return "\n".join(f"[round {t.round}] {t.side}: {t.argument}" for t in turns)


def _prompt(
    initiative: Initiative,
    reports: list[AnalystReport],
    debate: list[DebateTurn],
) -> str:
    return (
        "You are a Product Strategist. Synthesize the analyst reports AND the "
        "advocate/skeptic debate below into a single recommendation. Provide a "
        "recommendation, a confidence score between 0 and 1, a rationale, and "
        "expected outcomes.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        f"Analyst reports:\n{_format_reports(reports)}\n\n"
        f"Debate transcript:\n{_format_debate(debate)}\n"
    )


async def strategist_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": NODE_ID, "status": "synthesizing recommendation…"})
    structured = model.with_structured_output(Recommendation)
    try:
        recommendation = await structured.ainvoke(
            _prompt(
                state["initiative"],
                state["reports"],
                state.get("debate", []),
            )
        )
        writer({"node": NODE_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "status": f"failed: {exc}"})
        recommendation = Recommendation(
            recommendation="Unable to produce a recommendation due to an error.",
            confidence=0.0,
            rationale=f"Strategist failed: {exc}",
            expected_outcomes=[],
        )
    return {"recommendation": recommendation}
