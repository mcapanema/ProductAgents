"""Product Strategist node: synthesizes analyst reports and the debate."""

from productagents.agents._format import format_transcript
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


def _format_lessons(lessons: list[str]) -> str:
    if not lessons:
        return "(no relevant past lessons)"
    return "\n".join(f"- {lesson}" for lesson in lessons)


def _format_critique(judgment) -> str:
    if judgment is None:
        return ""
    return (
        "\n\nIMPORTANT - a prior version of your recommendation was reviewed by a "
        "quality judge and did NOT pass. Revise it to address this critique:\n"
        f"- Evidence grounding score: {judgment.evidence_grounding_score:.2f} "
        "(improve this)\n"
        f"- Rationale coherence score: {judgment.rationale_coherence_score:.2f} "
        "(improve this)\n"
        f"- Critique: {judgment.critique}\n"
    )


def _prompt(
    initiative: Initiative,
    reports: list[AnalystReport],
    debate: list[DebateTurn],
    prior_lessons: list[str],
    judgment=None,
) -> str:
    return (
        "You are a Product Strategist. Synthesize the analyst reports AND the "
        "advocate/skeptic debate below into a single recommendation. Provide a "
        "recommendation, a confidence score between 0 and 1, a rationale, and "
        "expected outcomes. Apply the lessons from past decisions where they are "
        "relevant.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        f"Analyst reports:\n{_format_reports(reports)}\n\n"
        f"Debate transcript:\n{format_transcript(debate)}\n\n"
        f"Lessons from past decisions:\n{_format_lessons(prior_lessons)}\n"
        f"{_format_critique(judgment)}"
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
                state.get("prior_lessons", []),
                state.get("judgment"),
            )
        )
        writer({"node": NODE_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "error": str(exc)})
        recommendation = Recommendation(
            recommendation="Unable to produce a recommendation due to an error.",
            confidence=0.0,
            rationale=f"Strategist failed: {exc}",
            expected_outcomes=[],
        )
    return {"recommendation": recommendation}
