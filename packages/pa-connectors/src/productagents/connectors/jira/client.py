"""HTTP access to Jira Cloud issues: JQL build, nextPageToken pagination.

Issues are searched ``ORDER BY updated ASC`` so the last issue on the last page
carries the maximum ``updated`` — that becomes the next cursor. JQL filters on
minute granularity (``"yyyy-MM-dd HH:mm"``); boundary issues re-emitted on the
next run dedupe on ``(connector, vendor_type, vendor_id)`` in the sink.
"""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx

from productagents.connectors.http import request_with_retry

JIRA_HEADERS = {"Accept": "application/json"}
_SEARCH_PATH = "/rest/api/3/search"
_FIELDS = "summary,description,reporter,created,updated,labels"


def _jql_since(since: str) -> str:
    """Format an ISO8601 cursor as JQL's ``yyyy-MM-dd HH:mm`` minute precision."""
    return datetime.fromisoformat(since).strftime("%Y-%m-%d %H:%M")


def build_jql(*, project: str | None, since: str | None) -> str:
    """Assemble the JQL query: optional project + optional ``updated >=`` filter."""
    clauses: list[str] = []
    if project:
        clauses.append(f'project = "{project}"')
    if since:
        clauses.append(f'updated >= "{_jql_since(since)}"')
    where = " AND ".join(clauses)
    return f"{where} ORDER BY updated ASC" if where else "ORDER BY updated ASC"


class JiraClient:
    """Pages through one site's issues over a provided httpx client."""

    def __init__(self, http: httpx.AsyncClient, *, project: str | None) -> None:
        self._http = http
        self._project = project

    async def iter_issues(self, *, since: str | None) -> AsyncIterator[dict]:
        """Yield every issue matching the JQL, oldest-updated first, since cursor."""
        params: dict[str, str] = {
            "jql": build_jql(project=self._project, since=since),
            "maxResults": "100",
            "fields": _FIELDS,
        }
        token: str | None = None
        while True:
            page_params = dict(params)
            if token:
                page_params["nextPageToken"] = token
            response = await request_with_retry(
                self._http, "GET", _SEARCH_PATH, params=page_params
            )
            body = response.json()
            for issue in body.get("issues") or ():
                yield issue
            token = body.get("nextPageToken")
            if not token:
                return
