"""Quality Judge node: an LLM-as-Judge gate on the strategist's recommendation.

Runs after the strategist. Scores the recommendation on evidence grounding and
rationale coherence (each 0-1) and computes a deterministic pass/fail from a
configurable threshold. The graph uses the verdict to route the recommendation
forward to risk or back to the strategist for a bounded revision.
"""

from productagents.agents._format import (
    format_initiative,
    format_recommendation,
    format_reports_brief,
    format_transcript,
)
from productagents.agents._llm_call import invoke_structured
from productagents.agents._stream import get_writer
from productagents.config import env_float, env_int
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Initiative,
    JudgeFinding,
    JudgeVerdict,
    Recommendation,
)

NODE_ID = "judge"

DEFAULT_JUDGE_THRESHOLD = 0.7
# Max times the judge sends the strategist back to revise. Default 1.
# 0 = score-only: the judge still scores and surfaces a verdict, but never
# loops back to the strategist (the gate becomes purely advisory).
DEFAULT_JUDGE_MAX_RETRIES = 1


def get_judge_threshold() -> float:
    """Return the configured pass threshold for both dimensions (default 0.7)."""
    return env_float(
        "PRODUCTAGENTS_JUDGE_THRESHOLD",
        DEFAULT_JUDGE_THRESHOLD,
        minimum=0.0,
        maximum=1.0,
    )


def get_judge_max_retries() -> int:
    """Return the configured max strategist revisions (default 1; 0 = score-only)."""
    return env_int(
        "PRODUCTAGENTS_JUDGE_MAX_RETRIES", DEFAULT_JUDGE_MAX_RETRIES, minimum=0
    )


def _prompt(
    initiative: Initiative,
    recommendation: Recommendation,
    reports: list[AnalystReport],
    debate: list[DebateTurn],
) -> str:
    return (
        "You are a meticulous Quality Judge reviewing a product recommendation. "
        "Score it on two dimensions, each from 0.0 to 1.0:\n"
        "- evidence_grounding: is every claim supported by the analyst findings "
        "and signals below, with no unsupported assertions?\n"
        "- rationale_coherence: does the conclusion follow logically from the "
        "stated rationale and expected outcomes, with no internal contradictions?\n"
        "Also give a short, specific, actionable critique the strategist can use "
        "to revise.\n\n"
        f"{format_initiative(initiative)}\n\n"
        f"{format_recommendation(recommendation)}\n\n"
        f"Analyst findings:\n{format_reports_brief(reports)}\n\n"
        f"Debate transcript:\n{format_transcript(debate)}\n"
    )


async def judge_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": NODE_ID, "status": "judging recommendation..."})
    attempt = state.get("judge_attempts", 0) + 1
    threshold = get_judge_threshold()
    try:
        finding = await invoke_structured(
            model,
            JudgeFinding,
            _prompt(
                state["initiative"],
                state["recommendation"],
                state["reports"],
                state.get("debate", []),
            ),
            node=NODE_ID,
        )
        passed = (
            finding.evidence_grounding_score >= threshold
            and finding.rationale_coherence_score >= threshold
        )
        verdict = JudgeVerdict(
            evidence_grounding_score=finding.evidence_grounding_score,
            rationale_coherence_score=finding.rationale_coherence_score,
            passed=passed,
            critique=finding.critique,
            attempt=attempt,
        )
    except Exception as exc:  # noqa: BLE001 - degrade: a broken judge never blocks
        writer({"node": NODE_ID, "error": str(exc)})
        verdict = JudgeVerdict(
            evidence_grounding_score=0.0,
            rationale_coherence_score=0.0,
            passed=True,
            critique=f"(judge unavailable: {exc})",
            attempt=attempt,
            failed=True,
        )
    writer({"node": NODE_ID, "judgment": verdict.model_dump()})
    return {"judgment": verdict, "judge_attempts": attempt}
