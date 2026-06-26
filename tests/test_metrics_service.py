"""MetricsService searches metric definitions by free text."""

from productagents.core.models import ProductMetric
from productagents.knowledge.services.metrics_service import (
    MetricQuery,
    MetricsService,
)
from tests.knowledge_fakes import FakeRepository


def _corpus() -> list[ProductMetric]:
    return [
        ProductMetric(name="WAU", description="Weekly active users"),
        ProductMetric(name="Churn", description="Monthly logo churn"),
    ]


async def test_search_by_text_matches_name_and_description():
    svc = MetricsService(FakeRepository(_corpus()))
    page = await svc.search(MetricQuery(text="active"))
    assert [m.name for m in page.items] == ["WAU"]
    assert page.total == 1


async def test_empty_query_returns_all_metrics():
    svc = MetricsService(FakeRepository(_corpus()))
    page = await svc.search(MetricQuery())
    assert page.total == 2
