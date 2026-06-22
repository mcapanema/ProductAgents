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
from productagents.schemas import AnalystFindings, AnalystReport, Evidence, Initiative


async def run_analyst(
    state: dict,
    model,
    *,
    analyst_id: str,
    role: str,
    start_status: str,
    prompt: Callable[[Initiative, Evidence], str],
) -> dict:
    """Run one analyst's structured call, degrading to a failed report on error.

    Returns the `{"reports": [AnalystReport]}` partial state every analyst node
    contributes to the `reports` reducer.
    """
    writer = get_writer()
    writer({"node": analyst_id, "status": start_status})
    try:
        findings = await invoke_structured(
            model,
            AnalystFindings,
            prompt(state["initiative"], state["evidence"]),
            node=analyst_id,
        )
        report = AnalystReport(
            analyst=analyst_id,
            role=role,
            findings=findings.findings,
            signals=findings.signals,
        )
        writer({"node": analyst_id, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": analyst_id, "error": str(exc)})
        report = AnalystReport(
            analyst=analyst_id, role=role, findings=[], signals=[], failed=True
        )
    return {"reports": [report]}
