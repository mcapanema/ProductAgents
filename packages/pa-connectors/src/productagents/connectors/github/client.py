"""HTTP access to GitHub issues: auth, pagination, incremental `since` filter.

Issues are fetched sorted by ``updated`` ascending so the last issue on the last
page carries the maximum ``updated_at`` — that becomes the next cursor. GitHub
returns pull requests in the issues endpoint; they are filtered out here so the
mapper only ever sees real issues.
"""

from collections.abc import AsyncIterator

import httpx

from productagents.connectors.http import request_with_retry

GITHUB_API = "https://api.github.com"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


class GitHubClient:
    """Pages through one repo's issues over a provided httpx client."""

    def __init__(self, http: httpx.AsyncClient, owner: str, repo: str) -> None:
        self._http = http
        self._owner = owner
        self._repo = repo

    async def iter_issues(self, *, since: str | None) -> AsyncIterator[dict]:
        """Yield every real issue (not a PR), newest-updated last, since cursor."""
        params: dict[str, str] = {
            "state": "all",
            "sort": "updated",
            "direction": "asc",
            "per_page": "100",
        }
        if since:
            params["since"] = since
        url: str | None = f"/repos/{self._owner}/{self._repo}/issues"
        while url is not None:
            response = await request_with_retry(
                self._http, "GET", url, params=params if url.startswith("/") else None
            )
            for item in response.json():
                if "pull_request" not in item:
                    yield item
            next_link = response.links.get("next")
            url = next_link["url"] if next_link else None
