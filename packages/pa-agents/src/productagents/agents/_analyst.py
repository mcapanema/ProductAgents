"""Shared execution helper for the five parallel analyst nodes.

Every analyst issues one structured `AnalystFindings` LLM call, wraps it in the
graceful-degradation contract, and emits the same start/done/failed progress
events. They differ only in identity (id/role), the opening status message, and
which `Evidence` fields their prompt renders. `run_analyst` captures the common
shape; each analyst module supplies its own constants and `_prompt` builder.
"""

from collections.abc import Callable

from productagents.agents._llm_call import invoke_structured
from productagents.agents._stream import get_writer
from productagents.agents.prompts import PromptStore
from productagents.agents.stream_events import emit_error, emit_status
from productagents.core.models import (
    AnalystFindings,
    AnalystReport,
    Evidence,
    Initiative,
)


async def run_analyst(
    state: dict,
    ctx,
    *,
    analyst_id: str,
    role: str,
    start_status: str,
    prompt: Callable[[Initiative, Evidence, PromptStore], str],
) -> dict:
    """Run one analyst's structured call, degrading to a failed report on error.

    Returns the `{"reports": [AnalystReport]}` partial state every analyst node
    contributes to the `reports` reducer. The chat model comes from `ctx.model`;
    nodes that read services reach them through other `ctx` fields.
    """
    writer = get_writer()
    writer(emit_status(analyst_id, start_status))
    try:
        findings = await invoke_structured(
            ctx.model,
            AnalystFindings,
            prompt(state["initiative"], state["evidence"], ctx.prompts),
            node=analyst_id,
        )
        report = AnalystReport(
            analyst=analyst_id,
            role=role,
            findings=findings.findings,
            signals=findings.signals,
        )
        writer(emit_status(analyst_id, "done"))
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer(emit_error(analyst_id, str(exc)))
        report = AnalystReport(
            analyst=analyst_id, role=role, findings=[], signals=[], failed=True
        )
    return {"reports": [report]}
