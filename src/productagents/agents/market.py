"""Market Analyst node: reads competitive and market evidence."""

from productagents.agents._analyst import run_analyst
from productagents.schemas import Evidence, Initiative

ANALYST_ID = "market"
ROLE = "Market Analyst"
_START_STATUS = "scanning the market…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the market intelligence below, identify competitive "
        "intelligence, market opportunities, and strategic context relevant to "
        "this initiative.\n\n"
        f"Market intelligence:\n{evidence.market_intelligence}\n"
    )


async def market_node(state: dict, model) -> dict:
    return await run_analyst(
        state,
        model,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
