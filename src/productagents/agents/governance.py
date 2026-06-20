"""Governance node: the Product Portfolio Manager approves, rejects, or
requests further analysis.

Runs last, after the risk team. The Portfolio Manager is the final decision
authority: it reviews the strategist's recommendation and the risk assessments,
weighs them against the recent portfolio of prior decisions, and asks not "is
this a good idea?" but "is this the best use of our limited resources right
now?" The verdict is emitted as a custom stream event for live rendering and
returned in graph state. Prior decisions arrive via state (read at the UI
boundary); the node never touches the filesystem.
"""

from productagents.agents._stream import get_writer
from productagents.schemas import (
    DecisionRecord,
    GovernanceFinding,
    GovernanceVerdict,
    Initiative,
    Recommendation,
    RiskAssessment,
)

NODE_ID = "governance"
ROLE = "Product Portfolio Manager"

# How many of the most recent prior decisions to show as portfolio context.
_PORTFOLIO_WINDOW = 5


def _format_recommendation(recommendation: Recommendation | None) -> str:
    if recommendation is None:
        return "(no recommendation)"
    return (
        f"{recommendation.recommendation} "
        f"(confidence {recommendation.confidence:.0%})\n"
        f"Rationale: {recommendation.rationale}\n"
        f"Expected outcomes: {recommendation.expected_outcomes}"
    )


def _format_risks(risks: list[RiskAssessment]) -> str:
    if not risks:
        return "(no risk assessments)"
    return "\n".join(f"- {r.role}: {r.level} — {r.rationale}" for r in risks)


def _format_portfolio(portfolio: list[DecisionRecord]) -> str:
    recent = portfolio[-_PORTFOLIO_WINDOW:]
    if not recent:
        return "(no prior decisions)"
    lines = []
    for record in recent:
        verdict = record.governance.verdict if record.governance else "n/a"
        lines.append(
            f"- {record.initiative.title}: "
            f"recommended '{record.recommendation.recommendation}', "
            f"governance verdict '{verdict}'"
        )
    return "\n".join(lines)


def _prompt(
    initiative: Initiative,
    recommendation: Recommendation | None,
    risks: list[RiskAssessment],
    portfolio: list[DecisionRecord],
) -> str:
    return (
        f"You are the {ROLE}, the final decision authority. You do not ask 'is "
        "this a good idea?' but 'is this the best use of our limited resources "
        "right now?' Review the recommendation and the risk assessments below, "
        "weigh them against the recent portfolio of prior decisions, and decide. "
        "Your verdict must be one of: approve, reject, request_analysis. Justify "
        "it.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        f"Recommendation:\n{_format_recommendation(recommendation)}\n\n"
        f"Risk assessments:\n{_format_risks(risks)}\n\n"
        f"Recent portfolio:\n{_format_portfolio(portfolio)}\n"
    )


async def governance_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": NODE_ID, "status": f"{ROLE} reviewing…"})
    structured = model.with_structured_output(GovernanceFinding)
    try:
        finding = await structured.ainvoke(
            _prompt(
                state["initiative"],
                state.get("recommendation"),
                state.get("risks", []),
                state.get("portfolio", []),
            )
        )
        verdict = GovernanceVerdict(
            verdict=finding.verdict,
            rationale=finding.rationale,
        )
        writer({"node": NODE_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "status": f"failed: {exc}"})
        verdict = GovernanceVerdict(
            verdict="error",
            rationale=f"({ROLE} unavailable: {exc})",
            failed=True,
        )
    writer({"node": NODE_ID, "verdict": verdict.model_dump()})
    return {"governance": verdict}
