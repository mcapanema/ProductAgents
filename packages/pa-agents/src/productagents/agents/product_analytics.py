"""Product Analytics Analyst node: reads quantitative usage evidence."""

import json

from productagents.agents._analyst import run_analyst
from productagents.agents._format import format_initiative
from productagents.agents.context import AgentContext
from productagents.core.models import Evidence, Initiative

ANALYST_ID = "product_analytics"
ROLE = "Product Analytics Analyst"
_START_STATUS = "analyzing product metrics…"


def _prompt(initiative: Initiative, evidence: Evidence, prompts) -> str:
    analytics = json.dumps(evidence.product_analytics, indent=2)
    return prompts.render(
        ANALYST_ID,
        initiative=format_initiative(initiative),
        evidence=analytics,
    )


async def product_analytics_node(state: dict, ctx: AgentContext) -> dict:
    return await run_analyst(
        state,
        ctx,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
