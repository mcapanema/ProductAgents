"""The Jira connector: issues → CustomerFeedback, incremental by ``updated``.

Health check and sync both degrade to a non-raising result so one bad site or a
dropped connection never aborts a batch (the runtime relies on this). The new
cursor is the maximum ``updated`` seen, so the next run's JQL ``since`` only
pulls newer issues; with no issues, the incoming cursor is preserved.

Jira Cloud uses HTTP Basic auth (``email:api_token``). We build that header here
and pass it through ``make_client``'s ``headers`` seam, so the shared http layer
(bearer-token shaped) needs no change.
"""

import base64
from typing import ClassVar

from productagents.connectors.base import (
    CanonicalSink,
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.connectors.connector_errors import classify_connector_error
from productagents.connectors.http import make_client
from productagents.connectors.jira.client import JIRA_HEADERS, JiraClient
from productagents.connectors.jira.mappers import issue_to_feedback
from productagents.core.models import CustomerFeedback


class JiraConfig(ConnectorConfig):
    """Typed config for the Jira connector, validated at construction."""

    base_url: str
    email: str
    token: str
    project: str | None = None


class JiraConnector(Connector):
    """Syncs a Jira site's issues into ``CustomerFeedback``."""

    key: ClassVar[str] = "jira"
    produces: ClassVar[frozenset[type]] = frozenset({CustomerFeedback})
    config_cls: ClassVar[type[ConnectorConfig]] = JiraConfig
    title: ClassVar[str] = "Jira"
    description: ClassVar[str] = "Syncs Jira issues into customer feedback."

    def __init__(self, config: JiraConfig, sink: CanonicalSink) -> None:
        super().__init__(config, sink)
        self._config = config

    def _client(self):
        raw = f"{self._config.email}:{self._config.token}".encode()
        auth = base64.b64encode(raw).decode()
        headers = {**JIRA_HEADERS, "Authorization": f"Basic {auth}"}
        return make_client(base_url=self._config.base_url, headers=headers)

    async def health_check(self) -> HealthStatus:
        try:
            async with self._client() as http:
                response = await http.get("/rest/api/3/myself")
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 — probe never raises
            return HealthStatus(ok=False, detail=str(classify_connector_error(exc)))
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        since = cursor.value if cursor else None
        latest = since
        written = 0
        try:
            async with self._client() as http:
                client = JiraClient(http, project=self._config.project)
                async for issue in client.iter_issues(since=since):
                    await self.sink.write(
                        issue_to_feedback(issue, base_url=self._config.base_url)
                    )
                    written += 1
                    updated = (issue.get("fields") or {}).get("updated")
                    if updated and (latest is None or updated > latest):
                        latest = updated
        except Exception as exc:  # noqa: BLE001 — degrade-don't-crash
            return SyncResult(
                connector=self.key,
                written=written,
                ok=False,
                error=str(classify_connector_error(exc)),
            )
        return SyncResult(
            connector=self.key, written=written, cursor=SyncCursor(value=latest)
        )
