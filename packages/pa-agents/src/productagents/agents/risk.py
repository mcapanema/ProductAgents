"""Risk Team node: five specialized reviewers assess the recommendation.

Runs after the strategist. Each reviewer (Delivery, Adoption, Strategic,
Financial, Organizational) sees the initiative, the analyst reports, the debate
transcript, and the strategist's recommendation, then returns a structured risk
level plus rationale. Each assessment is emitted as a custom stream event for
live rendering and collected into a structured list returned in graph state.
"""

from productagents.agents._format import (
    format_initiative,
    format_recommendation,
    format_reports_brief,
    format_transcript,
)
from productagents.agents._llm_call import invoke_structured
from productagents.agents._stream import get_writer
from productagents.agents.stream_events import (
    ASSESSMENT,
    emit_error,
    emit_payload,
    emit_status,
)
from productagents.core.models import (
    AnalystReport,
    DebateTurn,
    Initiative,
    Recommendation,
    RiskAssessment,
    RiskFinding,
)

NODE_ID = "risk"

# (reviewer_id, role) in fixed evaluation order.
REVIEWERS: list[tuple[str, str]] = [
    ("delivery", "Delivery Risk Reviewer"),
    ("adoption", "Adoption Risk Reviewer"),
    ("strategic", "Strategic Risk Reviewer"),
    ("financial", "Financial Risk Reviewer"),
    ("organizational", "Organizational Risk Reviewer"),
]

_FOCUS = {
    "delivery": "execution feasibility, delivery complexity, and technical risk",
    "adoption": "customer adoption risk and the chance users will not engage",
    "strategic": "alignment with organizational goals and strategic fit",
    "financial": "economic viability, cost, and expected return",
    "organizational": "team capacity and operational constraints",
}


def _prompt(
    reviewer: str,
    role: str,
    initiative: Initiative,
    reports: list[AnalystReport],
    debate: list[DebateTurn],
    recommendation: Recommendation,
) -> str:
    return (
        f"You are a {role}. Evaluate the {_FOCUS[reviewer]} of the recommendation "
        "below. Assign a risk level of low, medium, or high and justify it.\n\n"
        f"{format_initiative(initiative)}\n\n"
        f"{format_recommendation(recommendation)}\n\n"
        f"Analyst findings:\n{format_reports_brief(reports)}\n\n"
        f"Debate transcript:\n{format_transcript(debate)}\n"
    )


async def risk_node(state: dict, model) -> dict:
    writer = get_writer()
    assessments: list[RiskAssessment] = []
    for reviewer, role in REVIEWERS:
        writer(emit_status(NODE_ID, f"{role} assessing…"))
        try:
            finding = await invoke_structured(
                model,
                RiskFinding,
                _prompt(
                    reviewer,
                    role,
                    state["initiative"],
                    state["reports"],
                    state["debate"],
                    state["recommendation"],
                ),
                node=NODE_ID,
            )
            assessment = RiskAssessment(
                reviewer=reviewer,
                role=role,
                level=finding.level,
                rationale=finding.rationale,
            )
        except Exception as exc:  # noqa: BLE001 - degrade one reviewer, never crash
            writer(emit_error(NODE_ID, str(exc)))
            assessment = RiskAssessment(
                reviewer=reviewer,
                role=role,
                level="unknown",
                rationale=f"({role} unavailable: {exc})",
                failed=True,
            )
        assessments.append(assessment)
        writer(emit_payload(NODE_ID, ASSESSMENT, assessment))
    return {"risks": assessments}
