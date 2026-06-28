"""Technical Analyst node: reads architecture and delivery-complexity evidence."""

from productagents.agents._analyst import run_analyst
from productagents.agents._format import format_initiative
from productagents.core.models import Evidence, Initiative

ANALYST_ID = "technical"
ROLE = "Technical Analyst"
_START_STATUS = "assessing technical feasibility…"


def _prompt(initiative: Initiative, evidence: Evidence, prompts) -> str:
    return prompts.render(
        ANALYST_ID,
        initiative=format_initiative(initiative),
        evidence=evidence.technical_context,
    )


async def technical_node(state: dict, ctx) -> dict:
    return await run_analyst(
        state,
        ctx,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
