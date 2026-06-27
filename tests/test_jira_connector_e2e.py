"""End-to-end: Jira connector → canonical store → FeedbackService.

A connector pushes vendor data through the real sink, and the platform's public
service reads it back as canonical models, with neither layer knowing the other.
"""

import httpx
import respx

from productagents.connectors.jira.connector import JiraConfig, JiraConnector
from productagents.knowledge.container import build_services
from productagents.knowledge.services.feedback_service import FeedbackQuery
from productagents.knowledge.sink import DbCanonicalSink
from tests.storage_fixtures import memory_store

_BASE = "https://acme.atlassian.net"


def _config() -> JiraConfig:
    return JiraConfig(base_url=_BASE, email="me@acme.com", token="t", project="PROJ")


@respx.mock
async def test_synced_jira_issues_are_queryable_via_feedback_service():
    respx.get(url__startswith=f"{_BASE}/rest/api/3/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "PROJ-1",
                        "fields": {
                            "summary": "Add SSO",
                            "updated": "2026-01-10T00:00:00.000+0000",
                            "labels": ["auth"],
                        },
                    }
                ]
            },
        )
    )

    async with memory_store() as (sessionmaker, _engine):
        connector = JiraConnector(_config(), DbCanonicalSink(sessionmaker))

        result = await connector.sync(None)
        assert result.ok
        assert result.written == 1

        async with sessionmaker() as session:
            services = build_services(session)
            page = await services.feedback.search(FeedbackQuery())

    assert page.total == 1
    assert "Add SSO" in page.items[0].body
    assert page.items[0].source.connector == "jira"


@respx.mock
async def test_resync_is_idempotent_and_keeps_stable_id():
    issue = {
        "key": "PROJ-1",
        "fields": {
            "summary": "Add SSO",
            "updated": "2026-01-10T00:00:00.000+0000",
            "labels": [],
        },
    }
    respx.get(url__startswith=f"{_BASE}/rest/api/3/search").mock(
        side_effect=[
            httpx.Response(200, json={"issues": [issue]}),
            httpx.Response(200, json={"issues": [issue]}),
        ]
    )

    async with memory_store() as (sessionmaker, _engine):
        connector = JiraConnector(_config(), DbCanonicalSink(sessionmaker))
        await connector.sync(None)
        async with sessionmaker() as session:
            first = await build_services(session).feedback.search(FeedbackQuery())
        first_id = first.items[0].id

        await connector.sync(None)  # re-sync the same issue
        async with sessionmaker() as session:
            second = await build_services(session).feedback.search(FeedbackQuery())

    assert second.total == 1  # deduped on (connector, vendor_type, vendor_id)
    assert second.items[0].id == first_id  # platform id stable across re-sync
