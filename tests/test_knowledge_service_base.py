"""CanonicalQueryService wires get + scan/filter/paginate over a repository."""

from productagents.core.models import CustomerFeedback
from productagents.knowledge.services._query import Query
from productagents.knowledge.services._service import CanonicalQueryService
from tests.knowledge_fakes import FakeRepository


async def test_get_delegates_to_the_repository():
    fb = CustomerFeedback(body="hello")
    svc = CanonicalQueryService(FakeRepository([fb]))
    assert await svc.get(str(fb.id)) == fb


async def test_get_returns_none_for_unknown_id():
    svc = CanonicalQueryService(FakeRepository([CustomerFeedback(body="hi")]))
    assert await svc.get("nope") is None


async def test_search_with_default_query_returns_all_matches_paginated():
    items = [CustomerFeedback(body=f"f{i}") for i in range(5)]
    svc = CanonicalQueryService(FakeRepository(items))
    page = await svc.search(Query(limit=2, offset=0))
    assert len(page.items) == 2
    assert page.total == 5
    assert page.has_more is True


async def test_search_logs_warning_when_scan_limit_is_hit(caplog, monkeypatch):
    import productagents.knowledge.services._service as svc_mod

    items = [CustomerFeedback(body=f"f{i}") for i in range(2)]
    monkeypatch.setattr(svc_mod, "_SCAN_LIMIT", 2)
    svc = CanonicalQueryService(FakeRepository(items))
    with caplog.at_level("WARNING", logger="productagents.knowledge.services._service"):
        await svc.search(Query())
    assert any("scan limit" in record.message.lower() for record in caplog.records)
