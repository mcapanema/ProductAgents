from productagents.agents._analyst import run_analyst
from productagents.core.schemas import AnalystFindings, Evidence, Initiative
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "evidence": Evidence(
            scenario="sample",
            customer_feedback="Enterprises demand SSO.",
            product_analytics={},
        ),
    }


def _prompt(initiative, evidence):
    return f"{initiative.title} :: {evidence.customer_feedback}"


async def test_run_analyst_returns_report():
    model = FakeChatModel(
        {AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"])}
    )
    result = await run_analyst(
        _state(),
        model,
        analyst_id="demo",
        role="Demo Analyst",
        start_status="working…",
        prompt=_prompt,
    )
    report = result["reports"][0]
    assert report.analyst == "demo"
    assert report.role == "Demo Analyst"
    assert report.findings == ["demand"]
    assert report.signals == ["tickets"]
    assert report.failed is False


async def test_run_analyst_degrades_on_failure():
    model = FakeChatModel({AnalystFindings: RuntimeError("LLM down")})
    result = await run_analyst(
        _state(),
        model,
        analyst_id="demo",
        role="Demo Analyst",
        start_status="working…",
        prompt=_prompt,
    )
    report = result["reports"][0]
    assert report.failed is True
    assert report.findings == []
    assert report.signals == []
    assert report.analyst == "demo"


async def test_run_analyst_degrades_when_model_returns_none():
    # Reproduces "Product Analytics/Technical Analyst: 'NoneType' object has no
    # attribute 'findings'": a non-tool-calling model returns None.
    model = FakeChatModel({AnalystFindings: None})
    result = await run_analyst(
        _state(),
        model,
        analyst_id="demo",
        role="Demo Analyst",
        start_status="working…",
        prompt=_prompt,
    )
    report = result["reports"][0]
    assert report.failed is True
    assert report.findings == []
    assert report.signals == []
