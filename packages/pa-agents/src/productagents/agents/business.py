"""Business Analyst node: reads quantitative business and financial evidence."""

import json

from productagents.agents._analyst import run_analyst
from productagents.agents._format import format_initiative
from productagents.core.models import Evidence, Initiative

ANALYST_ID = "business"
ROLE = "Business Analyst"
_START_STATUS = "assessing business impact…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    metrics = json.dumps(evidence.business_metrics, indent=2)
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"{format_initiative(initiative)}\n\n"
        "Using ONLY the business metrics below, assess business impact, goal "
        "alignment, and ROI considerations relevant to this initiative.\n\n"
        f"Business metrics (JSON):\n{metrics}\n"
    )


async def business_node(state: dict, model) -> dict:
    return await run_analyst(
        state,
        model,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
