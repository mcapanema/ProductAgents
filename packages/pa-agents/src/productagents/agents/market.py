"""Market Analyst node: reads competitive and market evidence."""

from productagents.agents._analyst import run_analyst
from productagents.agents._format import format_initiative
from productagents.core.models import Evidence, Initiative

ANALYST_ID = "market"
ROLE = "Market Analyst"
_START_STATUS = "scanning the market…"


def _prompt(initiative: Initiative, evidence: Evidence, prompts) -> str:
    return prompts.render(
        ANALYST_ID,
        initiative=format_initiative(initiative),
        evidence=evidence.market_intelligence,
    )


async def market_node(state: dict, ctx) -> dict:
    return await run_analyst(
        state,
        ctx,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
