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

import logging

from productagents.agents._format import format_initiative, format_recommendation
from productagents.agents._llm_call import invoke_structured
from productagents.agents._stream import get_writer
from productagents.agents.prompts import PromptStore
from productagents.agents.stream_events import (
    VERDICT,
    emit_error,
    emit_payload,
    emit_status,
)
from productagents.core.models import (
    DecisionRecord,
    GovernanceFinding,
    GovernanceVerdict,
    Initiative,
    Recommendation,
    RiskAssessment,
)

logger = logging.getLogger(__name__)

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
    prompts: PromptStore,
) -> str:
    return prompts.render(
        "governance",
        initiative=format_initiative(initiative),
        recommendation=format_recommendation(recommendation),
        risks=_format_risks(risks),
        portfolio=_format_portfolio(portfolio),
    )


async def governance_node(state: dict, model, ctx) -> dict:
    writer = get_writer()
    writer(emit_status(NODE_ID, f"{ROLE} reviewing…"))
    try:
        portfolio = await ctx.learning.decisions()
    except Exception:  # noqa: BLE001 - degrade, never crash
        logger.warning(
            "governance: portfolio fetch failed; continuing without it",
            exc_info=True,
        )
        writer(emit_status(NODE_ID, "portfolio unavailable; continuing without it"))
        portfolio = []
    try:
        finding = await invoke_structured(
            model,
            GovernanceFinding,
            _prompt(
                state["initiative"],
                state.get("recommendation"),
                state.get("risks", []),
                portfolio,
                ctx.prompts,
            ),
            node=NODE_ID,
        )
        verdict = GovernanceVerdict(
            verdict=finding.verdict,
            rationale=finding.rationale,
        )
        writer(emit_status(NODE_ID, "done"))
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer(emit_error(NODE_ID, str(exc)))
        verdict = GovernanceVerdict(
            verdict="error",
            rationale=f"({ROLE} unavailable: {exc})",
            failed=True,
        )
    writer(emit_payload(NODE_ID, VERDICT, verdict))
    return {"governance": verdict}
