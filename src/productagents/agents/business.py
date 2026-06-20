"""Business Analyst node: reads quantitative business and financial evidence."""

import json

from productagents.agents._stream import get_writer
from productagents.schemas import AnalystFindings, AnalystReport, Evidence, Initiative

ANALYST_ID = "business"
ROLE = "Business Analyst"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    metrics = json.dumps(evidence.business_metrics, indent=2)
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the business metrics below, assess business impact, goal "
        "alignment, and ROI considerations relevant to this initiative.\n\n"
        f"Business metrics (JSON):\n{metrics}\n"
    )


async def business_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": ANALYST_ID, "status": "assessing business impact…"})
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
