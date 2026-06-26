"""Customer Research Analyst node: reads qualitative customer evidence.

Phase 5: feedback comes from the local canonical store (synced by connectors)
when present; otherwise the node degrades to the scenario evidence text. The
store read is local — it honors "no external fetch during agent execution".
"""

from productagents.agents._analyst import run_analyst
from productagents.agents._format import format_initiative
from productagents.agents._stream import get_writer
from productagents.core.models import Evidence, Initiative
from productagents.knowledge import FeedbackQuery

ANALYST_ID = "customer_research"
ROLE = "Customer Research Analyst"
_START_STATUS = "reading customer evidence…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"{format_initiative(initiative)}\n\n"
        "Using ONLY the customer feedback below, identify the key customer "
        "pain points and demand signals relevant to this initiative.\n\n"
        f"Customer feedback:\n{evidence.customer_feedback}\n"
    )


def _render_feedback(items) -> str:
    return "\n".join(f"- {f.body}" for f in items)


async def _resolve_evidence(state: dict, ctx) -> dict:
    """Return a state whose Evidence.customer_feedback prefers the store.

    Falls back to the scenario evidence (unchanged state) when the store is
    empty or unavailable; never raises.
    """
    evidence: Evidence = state["evidence"]
    try:
        page = await ctx.feedback.search(FeedbackQuery())
    except Exception as exc:  # noqa: BLE001 - store unavailable → scenario fallback
        get_writer()(
            {"node": ANALYST_ID, "status": f"store unavailable ({exc}); using scenario"}
        )
        return state
    if not page.items:
        return state
    get_writer()(
        {"node": ANALYST_ID, "status": f"{len(page.items)} feedback items from store"}
    )
    enriched = evidence.model_copy(
        update={"customer_feedback": _render_feedback(page.items)}
    )
    return {**state, "evidence": enriched}


async def customer_research_node(state: dict, ctx) -> dict:
    resolved = await _resolve_evidence(state, ctx)
    return await run_analyst(
        resolved,
        ctx,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
