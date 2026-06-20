"""Product Analytics Analyst node: reads quantitative usage evidence."""

import json

from productagents.agents._stream import get_writer
from productagents.schemas import AnalystFindings, AnalystReport, Evidence, Initiative

ANALYST_ID = "product_analytics"
ROLE = "Product Analytics Analyst"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    analytics = json.dumps(evidence.product_analytics, indent=2)
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the product analytics below, identify behavioral insights, "
        "impact estimates, and opportunity sizing relevant to this initiative.\n\n"
        f"Product analytics (JSON):\n{analytics}\n"
    )


async def product_analytics_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": ANALYST_ID, "status": "analyzing product metrics…"})
    structured = model.with_structured_output(AnalystFindings)
    try:
        findings = await structured.ainvoke(
            _prompt(state["initiative"], state["evidence"])
        )
        report = AnalystReport(
            analyst=ANALYST_ID,
            role=ROLE,
            findings=findings.findings,
            signals=findings.signals,
        )
        writer({"node": ANALYST_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": ANALYST_ID, "status": f"failed: {exc}"})
        report = AnalystReport(
            analyst=ANALYST_ID, role=ROLE, findings=[], signals=[], failed=True
        )
    return {"reports": [report]}
