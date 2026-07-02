"""The GitHub connector: health check, sync (happy + degrade)."""

import httpx
import respx

from productagents.connectors.base import SyncCursor
from productagents.connectors.github.client import GITHUB_API
from productagents.connectors.github.connector import GitHubConfig, GitHubConnector
from tests.connector_fakes import FakeSink


def _config() -> GitHubConfig:
    return GitHubConfig(owner="acme", repo="app", token="t")


@respx.mock
async def test_health_check_ok():
    respx.get(f"{GITHUB_API}/repos/acme/app").mock(return_value=httpx.Response(200))
    status = await GitHubConnector(_config(), FakeSink()).health_check()
    assert status.ok is True


@respx.mock
async def test_health_check_degrades_on_error():
    respx.get(f"{GITHUB_API}/repos/acme/app").mock(return_value=httpx.Response(404))
    status = await GitHubConnector(_config(), FakeSink()).health_check()
    assert status.ok is False
    assert status.detail  # carries some diagnostic text


@respx.mock
async def test_sync_writes_feedback_and_advances_cursor():
    respx.get(url__startswith=f"{GITHUB_API}/repos/acme/app/issues").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"number": 1, "title": "a", "updated_at": "2026-01-10T00:00:00Z"},
                {"number": 2, "title": "b", "updated_at": "2026-01-12T00:00:00Z"},
            ],
        )
    )
    sink = FakeSink()

    result = await GitHubConnector(_config(), sink).sync(None)

    assert result.ok is True
    assert result.written == 2
    assert result.cursor is not None
    assert result.cursor.value == "2026-01-12T00:00:00Z"  # max updated_at
    assert {fb.source.vendor_id for fb in sink.written} == {"1", "2"}


@respx.mock
async def test_sync_keeps_incoming_cursor_when_no_issues():
    respx.get(url__startswith=f"{GITHUB_API}/repos/acme/app/issues").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await GitHubConnector(_config(), FakeSink()).sync(
        SyncCursor(value="2026-01-01T00:00:00Z")
    )
    assert result.written == 0
    assert result.cursor is not None
    assert result.cursor.value == "2026-01-01T00:00:00Z"


@respx.mock
async def test_sync_degrades_on_transport_failure():
    respx.get(url__startswith=f"{GITHUB_API}/repos/acme/app/issues").mock(
        side_effect=httpx.ConnectError("no network")
    )
    result = await GitHubConnector(_config(), FakeSink()).sync(None)
    assert result.ok is False
    assert result.error
    assert result.connector == "github"


async def test_health_check_returns_friendly_auth_message():
    config = GitHubConfig(owner="o", repo="r", token="bad")
    connector = GitHubConnector(config, sink=FakeSink())  # sink unused by health
    with respx.mock:
        respx.get("https://api.github.com/repos/o/r").mock(
            return_value=httpx.Response(401)
        )
        status = await connector.health_check()
    assert status.ok is False
    assert "Authentication failed" in status.detail
