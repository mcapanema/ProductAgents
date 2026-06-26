"""The GitHub issue client: pagination, `since` cursor, PR filtering."""

import httpx
import respx

from productagents.connectors.github.client import GITHUB_API, GitHubClient


async def _collect(since: str | None) -> list[dict]:
    async with httpx.AsyncClient(base_url=GITHUB_API) as http:
        client = GitHubClient(http, "acme", "app")
        return [issue async for issue in client.iter_issues(since=since)]


@respx.mock
async def test_paginates_via_link_header():
    page1 = httpx.Response(
        200,
        json=[{"number": 1, "title": "a"}, {"number": 2, "title": "b"}],
        headers={"Link": f'<{GITHUB_API}/repos/acme/app/issues?page=2>; rel="next"'},
    )
    page2 = httpx.Response(200, json=[{"number": 3, "title": "c"}])
    respx.get(url__startswith=f"{GITHUB_API}/repos/acme/app/issues").mock(
        side_effect=[page1, page2]
    )

    issues = await _collect(since=None)

    assert [i["number"] for i in issues] == [1, 2, 3]


@respx.mock
async def test_filters_out_pull_requests():
    respx.get(url__startswith=f"{GITHUB_API}/repos/acme/app/issues").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"number": 1, "title": "real issue"},
                {"number": 2, "title": "a PR", "pull_request": {"url": "..."}},
            ],
        )
    )

    issues = await _collect(since=None)

    assert [i["number"] for i in issues] == [1]


@respx.mock
async def test_sends_since_param_when_given():
    route = respx.get(url__startswith=f"{GITHUB_API}/repos/acme/app/issues").mock(
        return_value=httpx.Response(200, json=[])
    )

    await _collect(since="2026-01-01T00:00:00+00:00")

    request = route.calls.last.request
    assert request.url.params["since"] == "2026-01-01T00:00:00+00:00"
    assert request.url.params["state"] == "all"
