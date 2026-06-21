"""Product Analytics Analyst node: reads quantitative usage evidence."""

import json

from productagents.agents._analyst import run_analyst
from productagents.schemas import Evidence, Initiative

ANALYST_ID = "product_analytics"
ROLE = "Product Analytics Analyst"
_START_STATUS = "analyzing product metrics…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    analytics = json.dumps(evidence.product_analytics, indent=2)
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the product analytics below, identify behavioral insights, "
        "impact estimates, and opportunity sizing relevant to this initiative.\n\n"
        f"Product analytics (JSON):\n{analytics}\n"
    )


async def product_analytics_node(state: dict, model) -> dict:
    return await run_analyst(
        state,
        model,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
