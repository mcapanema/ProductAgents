"""Reflection agent: evaluate the actual outcome of a past decision.

This is the capture half of Outcome Learning. It runs after the fact (not in
the decision graph): given a past DecisionRecord and a free-text note describing
what actually happened, it compares the predicted expected outcomes against
reality and produces a structured OutcomeRecord (actual outcomes, prediction
accuracy, lessons learned). Like every other agent it degrades on failure rather
than crashing.
"""

from datetime import UTC, datetime

from productagents.agents._format import format_initiative
from productagents.agents._llm_call import invoke_structured
from productagents.agents.prompts import PromptStore
from productagents.core.models import DecisionRecord, OutcomeRecord, Reflection

ROLE = "Outcome Reflection Analyst"


def _prompt(decision: DecisionRecord, outcome_note: str, prompts: PromptStore) -> str:
    rec = decision.recommendation
    return prompts.render(
        "reflection",
        initiative=format_initiative(decision.initiative),
        recommendation=rec.recommendation,
        confidence=rec.confidence,
        expected_outcomes=rec.expected_outcomes,
        outcome_note=outcome_note,
    )


async def reflect(
    decision: DecisionRecord,
    outcome_note: str,
    model,
    prompts: PromptStore | None = None,
) -> OutcomeRecord:
    store = prompts or PromptStore()
    reflected_at = datetime.now(UTC).isoformat()
    try:
        reflection = await invoke_structured(
            model, Reflection, _prompt(decision, outcome_note, store), node="reflection"
        )
        return OutcomeRecord(
            decision_id=decision.decision_id,
            actual_outcomes=reflection.actual_outcomes,
            prediction_accuracy=reflection.prediction_accuracy,
            lessons_learned=reflection.lessons_learned,
            reflected_at=reflected_at,
        )
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash
        return OutcomeRecord(
            decision_id=decision.decision_id,
            actual_outcomes=[],
            prediction_accuracy=0.0,
            lessons_learned=[f"(Reflection unavailable: {exc})"],
            reflected_at=reflected_at,
            failed=True,
        )
