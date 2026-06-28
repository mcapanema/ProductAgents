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
from productagents.agents.prompts import PromptStore
from productagents.agents.stream_events import (
    JUDGMENT,
    emit_error,
    emit_payload,
    emit_status,
)
from productagents.core.config import env_float, env_int
from productagents.core.models import (
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
    prompts: PromptStore,
) -> str:
    return prompts.render(
        "judge",
        initiative=format_initiative(initiative),
        recommendation=format_recommendation(recommendation),
        reports=format_reports_brief(reports),
        debate=format_transcript(debate),
    )


async def judge_node(state: dict, model, prompts: PromptStore | None = None) -> dict:
    store = prompts or PromptStore()
    writer = get_writer()
    writer(emit_status(NODE_ID, "judging recommendation..."))
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
                store,
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
        writer(emit_error(NODE_ID, str(exc)))
        verdict = JudgeVerdict(
            evidence_grounding_score=0.0,
            rationale_coherence_score=0.0,
            passed=True,
            critique=f"(judge unavailable: {exc})",
            attempt=attempt,
            failed=True,
        )
    writer(emit_payload(NODE_ID, JUDGMENT, verdict))
    return {"judgment": verdict, "judge_attempts": attempt}
