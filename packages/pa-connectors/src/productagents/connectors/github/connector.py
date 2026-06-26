"""The GitHub connector: issues → CustomerFeedback, incremental by `updated_at`.

Health check and sync both degrade to a non-raising result so one bad repo or a
dropped connection never aborts a batch (the runtime relies on this). The new
cursor is the maximum ``updated_at`` seen, so the next run's ``since`` only pulls
newer issues; with no issues, the incoming cursor is preserved.
"""

import os
from typing import ClassVar

from productagents.connectors.base import (
    CanonicalSink,
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.connectors.github.client import (
    GITHUB_API,
    GITHUB_HEADERS,
    GitHubClient,
)
from productagents.connectors.github.mappers import issue_to_feedback
from productagents.connectors.http import make_client
from productagents.core.models import CustomerFeedback


class GitHubConfig(ConnectorConfig):
    """Typed config for the GitHub connector, validated at construction."""

    owner: str
    repo: str
    token: str | None = None

    @classmethod
    def from_env(cls) -> GitHubConfig | None:
        """Build from ``PRODUCTAGENTS_GITHUB_REPO`` (``owner/repo``) + token.

        Returns ``None`` when the repo is unset — i.e. the connector is disabled.
        """
        repo_spec = os.environ.get("PRODUCTAGENTS_GITHUB_REPO")
        if not repo_spec or "/" not in repo_spec:
            return None
        owner, repo = repo_spec.split("/", 1)
        return cls(
            owner=owner, repo=repo, token=os.environ.get("PRODUCTAGENTS_GITHUB_TOKEN")
        )


class GitHubConnector(Connector):
    """Syncs a repo's issues into ``CustomerFeedback``."""

    key: ClassVar[str] = "github"
    produces: ClassVar[frozenset[type]] = frozenset({CustomerFeedback})

    def __init__(self, config: GitHubConfig, sink: CanonicalSink) -> None:
        super().__init__(config, sink)
        self._config = config

    def _client(self):
        return make_client(
            base_url=GITHUB_API, token=self._config.token, headers=GITHUB_HEADERS
        )

    async def health_check(self) -> HealthStatus:
        try:
            async with self._client() as http:
                response = await http.get(
                    f"/repos/{self._config.owner}/{self._config.repo}"
                )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 — probe never raises
            return HealthStatus(ok=False, detail=str(exc))
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        since = cursor.value if cursor else None
        latest = since
        written = 0
        try:
            async with self._client() as http:
                client = GitHubClient(http, self._config.owner, self._config.repo)
                async for issue in client.iter_issues(since=since):
                    await self.sink.write(issue_to_feedback(issue))
                    written += 1
                    updated = issue.get("updated_at")
                    if updated and (latest is None or updated > latest):
                        latest = updated
        except Exception as exc:  # noqa: BLE001 — degrade-don't-crash
            return SyncResult(
                connector=self.key, written=written, ok=False, error=str(exc)
            )
        return SyncResult(
            connector=self.key, written=written, cursor=SyncCursor(value=latest)
        )
