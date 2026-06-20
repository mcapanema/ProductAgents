"""Technical Analyst node: reads architecture and delivery-complexity evidence."""

from productagents.agents._stream import get_writer
from productagents.schemas import AnalystFindings, AnalystReport, Evidence, Initiative

ANALYST_ID = "technical"
ROLE = "Technical Analyst"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the technical context below, assess feasibility, technical "
        "risks, and effort and delivery complexity relevant to this initiative.\n\n"
        f"Technical context:\n{evidence.technical_context}\n"
    )


async def technical_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": ANALYST_ID, "status": "assessing technical feasibility…"})
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
