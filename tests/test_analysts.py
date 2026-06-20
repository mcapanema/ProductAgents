import pytest

from productagents.agents.customer_research import customer_research_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.schemas import AnalystFindings, Evidence, Initiative
from tests.fakes import FakeChatModel


@pytest.fixture
def state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "evidence": Evidence(
            scenario="sample",
            customer_feedback="Enterprises demand SSO.",
            product_analytics={"onboarding_drop_off_rate": 0.3},
            business_metrics={"arr": 1350000},
        ),
    }


async def test_customer_research_returns_report(state):
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(
                findings=["demand for SSO"], signals=["18 tickets"]
            )
        }
    )
    result = await customer_research_node(state, model)
    reports = result["reports"]
    assert len(reports) == 1
    report = reports[0]
    assert report.analyst == "customer_research"
    assert report.role == "Customer Research Analyst"
    assert report.findings == ["demand for SSO"]
    assert report.failed is False


async def test_product_analytics_returns_report(state):
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(
                findings=["30% drop-off"], signals=["funnel data"]
            )
        }
    )
    result = await product_analytics_node(state, model)
    report = result["reports"][0]
    assert report.analyst == "product_analytics"
    assert report.role == "Product Analytics Analyst"
    assert report.findings == ["30% drop-off"]


async def test_analyst_failure_yields_degraded_report(state):
    model = FakeChatModel({AnalystFindings: RuntimeError("LLM down")})
    result = await customer_research_node(state, model)
    report = result["reports"][0]
    assert report.failed is True
    assert report.findings == []
    assert report.signals == []
    assert report.analyst == "customer_research"


from productagents.agents.market import market_node  # noqa: E402


async def test_market_returns_report(state):
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(
                findings=["rivals ship SSO"], signals=["3 competitors"]
            )
        }
    )
    result = await market_node(state, model)
    report = result["reports"][0]
    assert report.analyst == "market"
    assert report.role == "Market Analyst"
    assert report.findings == ["rivals ship SSO"]
    assert report.failed is False


async def test_market_degrades_on_failure(state):
    model = FakeChatModel({AnalystFindings: RuntimeError("LLM down")})
    result = await market_node(state, model)
    report = result["reports"][0]
    assert report.analyst == "market"
    assert report.failed is True
    assert report.findings == []
    assert report.signals == []


from productagents.agents.business import business_node  # noqa: E402


async def test_business_returns_report(state):
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(
                findings=["$1.35M pipeline blocked"], signals=["ARR data"]
            )
        }
    )
    result = await business_node(state, model)
    report = result["reports"][0]
    assert report.analyst == "business"
    assert report.role == "Business Analyst"
    assert report.findings == ["$1.35M pipeline blocked"]
    assert report.failed is False


async def test_business_degrades_on_failure(state):
    model = FakeChatModel({AnalystFindings: RuntimeError("LLM down")})
    result = await business_node(state, model)
    report = result["reports"][0]
    assert report.analyst == "business"
    assert report.failed is True
    assert report.findings == []
    assert report.signals == []
