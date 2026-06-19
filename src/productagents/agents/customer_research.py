"""Customer Research Analyst node: reads qualitative customer evidence."""

from productagents.agents._stream import get_writer
from productagents.schemas import AnalystFindings, AnalystReport, Evidence, Initiative

ANALYST_ID = "customer_research"
ROLE = "Customer Research Analyst"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the customer feedback below, identify the key customer "
        "pain points and demand signals relevant to this initiative.\n\n"
        f"Customer feedback:\n{evidence.customer_feedback}\n"
    )


async def customer_research_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": ANALYST_ID, "status": "reading customer evidence…"})
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
