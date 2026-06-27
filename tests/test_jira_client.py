"""The Jira issue client: JQL build, nextPageToken pagination, since filter."""

import httpx
import respx

from productagents.connectors.jira.client import JiraClient, build_jql

_BASE = "https://acme.atlassian.net"


def test_build_jql_orders_by_updated_ascending():
    assert build_jql(project=None, since=None) == "ORDER BY updated ASC"


def test_build_jql_adds_project_filter():
    jql = build_jql(project="PROJ", since=None)
    assert jql == 'project = "PROJ" ORDER BY updated ASC'


def test_build_jql_adds_since_in_minute_format():
    jql = build_jql(project=None, since="2026-01-16T10:30:45.000+0000")
    assert jql == 'updated >= "2026-01-15 10:30" ORDER BY updated ASC'


def test_build_jql_combines_project_and_since():
    jql = build_jql(project="PROJ", since="2026-01-16T10:30:45.000+0000")
    assert jql == (
        'project = "PROJ" AND updated >= "2026-01-15 10:30" ORDER BY updated ASC'
    )


async def _collect(since: str | None, *, project: str | None = None) -> list[dict]:
    async with httpx.AsyncClient(base_url=_BASE) as http:
        client = JiraClient(http, project=project)
        return [issue async for issue in client.iter_issues(since=since)]


@respx.mock
async def test_paginates_via_next_page_token():
    page1 = httpx.Response(
        200,
        json={
            "issues": [{"key": "P-1"}, {"key": "P-2"}],
            "nextPageToken": "tok2",
        },
    )
    page2 = httpx.Response(200, json={"issues": [{"key": "P-3"}]})  # no token = last
    respx.get(url__startswith=f"{_BASE}/rest/api/3/search").mock(
        side_effect=[page1, page2]
    )

    issues = await _collect(since=None)

    assert [i["key"] for i in issues] == ["P-1", "P-2", "P-3"]


@respx.mock
async def test_sends_jql_with_since_param():
    route = respx.get(url__startswith=f"{_BASE}/rest/api/3/search").mock(
        return_value=httpx.Response(200, json={"issues": []})
    )

    await _collect(since="2026-01-01T00:00:00.000+0000", project="PROJ")

    params = route.calls.last.request.url.params
    assert params["jql"] == (
        'project = "PROJ" AND updated >= "2025-12-31 00:00" ORDER BY updated ASC'
    )
    assert params["maxResults"] == "100"


@respx.mock
async def test_requests_enhanced_search_jql_endpoint():
    route = respx.get(url__startswith=f"{_BASE}/rest/api/3/search").mock(
        return_value=httpx.Response(200, json={"issues": []})
    )

    await _collect(since=None)

    assert route.calls.last.request.url.path == "/rest/api/3/search/jql"
