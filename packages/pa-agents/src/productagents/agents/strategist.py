"""Product Strategist node: synthesizes analyst reports and the debate."""

from productagents.agents._format import format_initiative, format_transcript
from productagents.agents._llm_call import invoke_structured
from productagents.agents._stream import get_writer
from productagents.agents.prompts import PromptStore
from productagents.agents.stream_events import emit_error, emit_status
from productagents.core.models import (
    AnalystReport,
    DebateTurn,
    Initiative,
    Recommendation,
)

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
    *,
    prompts: PromptStore,
) -> str:
    return prompts.render(
        "strategist",
        initiative=format_initiative(initiative),
        reports=_format_reports(reports),
        debate=format_transcript(debate),
        lessons=_format_lessons(prior_lessons),
        critique=_format_critique(judgment),
    )


async def strategist_node(
    state: dict, model, prompts: PromptStore | None = None
) -> dict:
    store = prompts or PromptStore()
    writer = get_writer()
    writer(emit_status(NODE_ID, "synthesizing recommendation…"))
    try:
        recommendation = await invoke_structured(
            model,
            Recommendation,
            _prompt(
                state["initiative"],
                state["reports"],
                state.get("debate", []),
                state.get("prior_lessons", []),
                state.get("judgment"),
                prompts=store,
            ),
            node=NODE_ID,
        )
        writer(emit_status(NODE_ID, "done"))
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer(emit_error(NODE_ID, str(exc)))
        recommendation = Recommendation(
            recommendation="Unable to produce a recommendation due to an error.",
            confidence=0.0,
            rationale=f"Strategist failed: {exc}",
            expected_outcomes=[],
            failed=True,
        )
    return {"recommendation": recommendation}
