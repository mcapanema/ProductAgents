"""Test doubles for the connector framework.

``FakeSink`` is the connector analogue of ``FakeChatModel``: it satisfies the
``CanonicalSink`` Protocol over an in-memory list, so a connector's ``sync`` can
be tested with no database.
"""

from collections.abc import Iterable

from productagents.connectors.base import (
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.core.models import CanonicalModel, CustomerFeedback


class FakeSink:
    """A ``CanonicalSink`` that records every written model."""

    def __init__(self) -> None:
        self.written: list[CanonicalModel] = []

    async def write(self, model: CanonicalModel) -> None:
        self.written.append(model)

    async def write_many(self, models: Iterable[CanonicalModel]) -> None:
        self.written.extend(models)


class WritingConnector(Connector):
    """A connector that writes ``count`` feedback rows and returns a cursor."""

    produces = frozenset({CustomerFeedback})

    def __init__(self, key: str, count: int, sink) -> None:
        self.key = key  # type: ignore
        super().__init__(ConnectorConfig(), sink)
        self._count = count

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        for i in range(self._count):
            await self.sink.write(CustomerFeedback(body=f"{self.key}-{i}"))
        return SyncResult(
            connector=self.key, written=self._count, cursor=SyncCursor(value="done")
        )


class FailingConnector(Connector):
    """A connector whose ``sync`` raises, to prove the runtime degrades it."""

    produces = frozenset({CustomerFeedback})

    def __init__(self, key: str, sink) -> None:
        self.key = key  # type: ignore
        super().__init__(ConnectorConfig(), sink)

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=False, detail="down")

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        raise RuntimeError("boom")
