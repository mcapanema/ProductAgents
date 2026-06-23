"""Human approval node: a human reviewer is the final governance authority.

Runs immediately after the LLM `governance` node, whose verdict is treated as
*advisory*. This node pauses the graph with LangGraph's `interrupt()`, surfacing
the advisory verdict to a human (via the runner's `approver` callback and the
TUI). The human's `HumanDecision` is fed back through `Command(resume=...)` and
becomes the binding `GovernanceVerdict` recorded for the decision. Added to the
graph only when `build_graph(model, human_in_the_loop=True)`.
"""

from langgraph.types import interrupt

from productagents.agents._stream import get_writer
from productagents.core.schemas import GovernanceVerdict

NODE_ID = "human_approval"


def _final_verdict(
    advisory: GovernanceVerdict | None, decision: dict
) -> GovernanceVerdict:
    """Assemble the binding verdict from the human's decision plus the AI advisory."""
    rationale = decision.get("rationale") or ""
    if not rationale and advisory is not None:
        rationale = advisory.rationale
    return GovernanceVerdict(
        verdict=decision["verdict"],
        rationale=rationale,
        decided_by="human",
        advisory_verdict=(
            advisory.verdict if advisory and advisory.verdict != "error" else None
        ),
        advisory_rationale=advisory.rationale if advisory else None,
    )


async def human_approval_node(state: dict) -> dict:
    advisory = state.get("governance")
    payload = {"advisory": advisory.model_dump() if advisory else None}
    # interrupt() pauses the graph; on resume it returns the Command(resume=...) value.
    decision = interrupt(payload)
    verdict = _final_verdict(advisory, decision)
    writer = get_writer()
    writer({"node": NODE_ID, "final_verdict": verdict.model_dump()})
    return {"governance": verdict}
