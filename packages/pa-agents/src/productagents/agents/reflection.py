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
from productagents.core.models import DecisionRecord, OutcomeRecord, Reflection

ROLE = "Outcome Reflection Analyst"


def _prompt(decision: DecisionRecord, outcome_note: str) -> str:
    rec = decision.recommendation
    return (
        f"You are an {ROLE}. A past product decision was made; now evaluate how it "
        "actually turned out. Compare the predicted expected outcomes against what "
        "actually happened, assign a prediction accuracy between 0 and 1, and "
        "extract concrete lessons for future decisions.\n\n"
        f"{format_initiative(decision.initiative)}\n\n"
        f"Recommendation made: {rec.recommendation}\n"
        f"Predicted confidence: {rec.confidence}\n"
        f"Expected outcomes (predicted): {rec.expected_outcomes}\n\n"
        f"What actually happened:\n{outcome_note}\n"
    )


async def reflect(decision: DecisionRecord, outcome_note: str, model) -> OutcomeRecord:
    reflected_at = datetime.now(UTC).isoformat()
    try:
        reflection = await invoke_structured(
            model, Reflection, _prompt(decision, outcome_note), node="reflection"
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
