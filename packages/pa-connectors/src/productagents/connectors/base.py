"""The connector contract: the ABC every connector implements + its value types.

A connector extracts vendor records, maps them to canonical models with pure
mappers, and pushes them to a ``CanonicalSink`` — which it knows only as a
Protocol. The concrete sink (``DbCanonicalSink``) lives in ``pa-knowledge`` and
satisfies this Protocol structurally, so a connector never imports the storage
layer and a third-party connector needs no ``pa-knowledge`` install to type-check.

ponytail: ``CanonicalSink`` is duplicated structurally with the (private) one in
``pa-knowledge``; that is deliberate — connectors must stay installable without
the storage package, and Protocols match by shape, so neither imports the other.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import ClassVar, Protocol

from pydantic import BaseModel

from productagents.core.models import CanonicalModel


class SyncCursor(BaseModel):
    """An opaque, vendor-shaped incremental-sync token (e.g. an ISO8601 marker).

    The runtime stores and threads it; only the connector interprets ``value``.
    """

    value: str | None = None


class HealthStatus(BaseModel):
    """The outcome of a connector readiness probe."""

    ok: bool
    detail: str = ""


class SyncResult(BaseModel):
    """The outcome of one ``sync`` run. ``ok=False`` means the run degraded."""

    connector: str
    written: int = 0
    cursor: SyncCursor | None = None
    ok: bool = True
    error: str | None = None


class ConnectorConfig(BaseModel):
    """Base config. Each connector subclasses it with its own typed fields."""

    enabled: bool = True


class CanonicalSink(Protocol):
    """Where a connector writes mapped canonical models, storage-agnostically."""

    async def write(self, model: CanonicalModel) -> None: ...

    async def write_many(self, models: Iterable[CanonicalModel]) -> None: ...


class Connector(ABC):
    """The contract every connector implements."""

    key: ClassVar[str]
    produces: ClassVar[frozenset[type[CanonicalModel]]]
    # The typed config schema this connector accepts. The app's YAML loader
    # validates a connector's config block against this, so adding a connector
    # needs no loader change. Defaults to the base so a no-config connector works.
    config_cls: ClassVar[type[ConnectorConfig]] = ConnectorConfig

    def __init__(self, config: ConnectorConfig, sink: CanonicalSink) -> None:
        self.config = config
        self.sink = sink

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Cheap readiness probe (auth + reachability). Never raises."""
        ...

    @abstractmethod
    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        """Extract since ``cursor``, map to canonical, write via ``self.sink``,
        return a new cursor. Idempotent on re-run. Never raises."""
        ...
