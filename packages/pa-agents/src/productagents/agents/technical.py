"""Technical Analyst node: reads architecture and delivery-complexity evidence."""

from productagents.agents._analyst import run_analyst
from productagents.agents._format import format_initiative
from productagents.core.models import Evidence, Initiative

ANALYST_ID = "technical"
ROLE = "Technical Analyst"
_START_STATUS = "assessing technical feasibility…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"{format_initiative(initiative)}\n\n"
        "Using ONLY the technical context below, assess feasibility, technical "
        "risks, and effort and delivery complexity relevant to this initiative.\n\n"
        f"Technical context:\n{evidence.technical_context}\n"
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
