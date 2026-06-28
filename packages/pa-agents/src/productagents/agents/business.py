"""Business Analyst node: reads quantitative business and financial evidence."""

import json

from productagents.agents._analyst import run_analyst
from productagents.agents._format import format_initiative
from productagents.core.models import Evidence, Initiative

ANALYST_ID = "business"
ROLE = "Business Analyst"
_START_STATUS = "assessing business impact…"


def _prompt(initiative: Initiative, evidence: Evidence, prompts) -> str:
    metrics = json.dumps(evidence.business_metrics, indent=2)
    return prompts.render(
        ANALYST_ID,
        initiative=format_initiative(initiative),
        evidence=metrics,
    )


async def business_node(state: dict, ctx) -> dict:
    return await run_analyst(
        state,
        ctx,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
