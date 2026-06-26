"""End-to-end: GitHub connector → canonical store → FeedbackService.

The architecture's payoff in one test — a connector pushes vendor data through
the real sink, and the platform's public service reads it back as canonical
models, with neither layer knowing about the other.
"""

import httpx
import respx

from productagents.connectors.github.client import GITHUB_API
from productagents.connectors.github.connector import GitHubConfig, GitHubConnector
from productagents.knowledge.container import build_services
from productagents.knowledge.services.feedback_service import FeedbackQuery
from productagents.knowledge.sink import DbCanonicalSink
from tests.storage_fixtures import memory_store


@respx.mock
async def test_synced_github_issues_are_queryable_via_feedback_service():
    respx.get(url__startswith=f"{GITHUB_API}/repos/acme/app/issues").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "number": 1,
                    "title": "Add SSO",
                    "body": "SAML please",
                    "updated_at": "2026-01-10T00:00:00Z",
                    "labels": [{"name": "auth"}],
                }
            ],
        )
    )

    async with memory_store() as (sessionmaker, _engine):
        connector = GitHubConnector(
            GitHubConfig(owner="acme", repo="app", token="t"),
            DbCanonicalSink(sessionmaker),
        )

        result = await connector.sync(None)
        assert result.ok
        assert result.written == 1

        async with sessionmaker() as session:
            services = build_services(session)
            page = await services.feedback.search(FeedbackQuery())

    assert page.total == 1
    assert "Add SSO" in page.items[0].body
    assert page.items[0].source.connector == "github"


@respx.mock
async def test_resync_is_idempotent_and_keeps_stable_id():
    issue = {
        "number": 1,
        "title": "Add SSO",
        "updated_at": "2026-01-10T00:00:00Z",
        "labels": [],
    }
    # ponytail: side_effect list — two syncs hit the endpoint twice
    respx.get(url__startswith=f"{GITHUB_API}/repos/acme/app/issues").mock(
        side_effect=[
            httpx.Response(200, json=[issue]),
            httpx.Response(200, json=[issue]),
        ]
    )

    async with memory_store() as (sessionmaker, _engine):
        connector = GitHubConnector(
            GitHubConfig(owner="acme", repo="app", token="t"),
            DbCanonicalSink(sessionmaker),
        )
        await connector.sync(None)
        async with sessionmaker() as session:
            first = await build_services(session).feedback.search(FeedbackQuery())
        first_id = first.items[0].id

        await connector.sync(None)  # re-sync the same issue
        async with sessionmaker() as session:
            second = await build_services(session).feedback.search(FeedbackQuery())

    assert second.total == 1  # deduped on (connector, vendor_type, vendor_id)
    assert second.items[0].id == first_id  # platform id stable across re-sync
