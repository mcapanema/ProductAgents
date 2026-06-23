"""Governance node: the Product Portfolio Manager provides an advisory
recommendation.

Runs last, after the risk team. The Portfolio Manager reviews the strategist's
recommendation and the risk assessments, weighs them against the recent
portfolio of prior decisions, and asks not "is this a good idea?" but "is this
the best use of our limited resources right now?" In Human-in-the-Loop runs,
this verdict is advisory; a human approver makes the final decision. The
verdict is emitted as a custom stream event for live rendering and returned in
graph state. Prior decisions arrive via state (read at the UI boundary); the
node never touches the filesystem.
"""

from productagents.core.schemas import (
    DecisionRecord,
    GovernanceFinding,
    GovernanceVerdict,
    Initiative,
    Recommendation,
    RiskAssessment,
)

from productagents.agents._format import format_initiative, format_recommendation
from productagents.agents._llm_call import invoke_structured
from productagents.agents._stream import get_writer

NODE_ID = "governance"
ROLE = "Product Portfolio Manager"

# How many of the most recent prior decisions to show as portfolio context.
_PORTFOLIO_WINDOW = 5


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
        f"You are the {ROLE}, providing an advisory recommendation. You do not "
        "ask 'is this a good idea?' but 'is this the best use of our limited "
        "resources right now?' Review the recommendation and the risk assessments "
        "below, weigh them against the recent portfolio of prior decisions, and "
        "provide your advisory verdict. Your verdict must be one of: approve, "
        "reject, request_analysis. Justify it.\n\n"
        f"{format_initiative(initiative)}\n\n"
        f"Recommendation:\n{format_recommendation(recommendation)}\n\n"
        f"Risk assessments:\n{_format_risks(risks)}\n\n"
        f"Recent portfolio:\n{_format_portfolio(portfolio)}\n"
    )


async def governance_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": NODE_ID, "status": f"{ROLE} reviewing…"})
    try:
        finding = await invoke_structured(
            model,
            GovernanceFinding,
            _prompt(
                state["initiative"],
                state.get("recommendation"),
                state.get("risks", []),
                state.get("portfolio", []),
            ),
            node=NODE_ID,
        )
        verdict = GovernanceVerdict(
            verdict=finding.verdict,
            rationale=finding.rationale,
        )
        writer({"node": NODE_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "error": str(exc)})
        verdict = GovernanceVerdict(
            verdict="error",
            rationale=f"({ROLE} unavailable: {exc})",
            failed=True,
        )
    writer({"node": NODE_ID, "verdict": verdict.model_dump()})
    return {"governance": verdict}
