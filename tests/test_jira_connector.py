"""The Jira connector: config typing, health check, sync (happy + degrade)."""

import httpx
import respx

from productagents.connectors.base import SyncCursor
from productagents.connectors.jira.connector import JiraConfig, JiraConnector
from tests.connector_fakes import FakeSink

_BASE = "https://acme.atlassian.net"


def _config() -> JiraConfig:
    return JiraConfig(base_url=_BASE, email="me@acme.com", token="t", project="PROJ")


def test_connector_declares_config_cls_seam():
    # The seam Phase 7a relies on: the app's YAML loader validates a 'jira:'
    # block against this class with no app code change.
    assert JiraConnector.config_cls is JiraConfig
    assert JiraConnector.key == "jira"


@respx.mock
async def test_health_check_ok():
    respx.get(f"{_BASE}/rest/api/3/myself").mock(return_value=httpx.Response(200))
    status = await JiraConnector(_config(), FakeSink()).health_check()
    assert status.ok is True


@respx.mock
async def test_health_check_degrades_on_error():
    respx.get(f"{_BASE}/rest/api/3/myself").mock(return_value=httpx.Response(401))
    status = await JiraConnector(_config(), FakeSink()).health_check()
    assert status.ok is False
    assert status.detail


@respx.mock
async def test_sync_writes_feedback_and_advances_cursor():
    route = respx.get(url__startswith=f"{_BASE}/rest/api/3/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "PROJ-1",
                        "fields": {
                            "summary": "a",
                            "updated": "2026-01-10T00:00:00.000+0000",
                        },
                    },
                    {
                        "key": "PROJ-2",
                        "fields": {
                            "summary": "b",
                            "updated": "2026-01-12T00:00:00.000+0000",
                        },
                    },
                ]
            },
        )
    )
    sink = FakeSink()

    result = await JiraConnector(_config(), sink).sync(None)

    assert result.ok is True
    assert result.written == 2
    assert result.cursor is not None
    assert result.cursor.value == "2026-01-12T00:00:00.000+0000"  # max updated
    assert {fb.source.vendor_id for fb in sink.written} == {"PROJ-1", "PROJ-2"}
    # Basic auth header was sent (no token in URL, header instead).
    auth = route.calls.last.request.headers["authorization"]
    assert auth.startswith("Basic ")


@respx.mock
async def test_sync_keeps_incoming_cursor_when_no_issues():
    respx.get(url__startswith=f"{_BASE}/rest/api/3/search").mock(
        return_value=httpx.Response(200, json={"issues": []})
    )
    result = await JiraConnector(_config(), FakeSink()).sync(
        SyncCursor(value="2026-01-01T00:00:00.000+0000")
    )
    assert result.written == 0
    assert result.cursor is not None
    assert result.cursor.value == "2026-01-01T00:00:00.000+0000"


@respx.mock
async def test_sync_degrades_on_transport_failure():
    respx.get(url__startswith=f"{_BASE}/rest/api/3/search").mock(
        side_effect=httpx.ConnectError("no network")
    )
    result = await JiraConnector(_config(), FakeSink()).sync(None)
    assert result.ok is False
    assert result.error
    assert result.connector == "jira"


async def test_health_check_returns_friendly_message_on_auth_failure():
    config = JiraConfig(
        base_url="https://acme.atlassian.net",
        email="a@b.com",
        token="bad",
    )
    connector = JiraConnector(config, sink=FakeSink())
    with respx.mock:
        respx.get("https://acme.atlassian.net/rest/api/3/myself").mock(
            return_value=httpx.Response(401)
        )
        status = await connector.health_check()
    assert status.ok is False
    assert "Authentication failed" in status.detail
