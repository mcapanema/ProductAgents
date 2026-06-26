"""Customer Research Analyst node: reads qualitative customer evidence."""

from productagents.agents._analyst import run_analyst
from productagents.agents._format import format_initiative
from productagents.core.models import Evidence, Initiative

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


async def customer_research_node(state: dict, ctx) -> dict:
    return await run_analyst(
        state,
        ctx,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
