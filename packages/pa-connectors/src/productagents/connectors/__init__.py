"""ProductAgents connector framework (Layer 1).

Connectors extract from external systems and map into canonical models, pushing
to a ``CanonicalSink`` and staying ignorant of storage. Discovery is via the
``productagents.connectors`` entry-point group; the runtime syncs enabled
connectors concurrently and degrades any failure into a result.
"""

from productagents.connectors.base import (
    CanonicalSink,
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.connectors.registry import discover
from productagents.connectors.runtime import run_sync

__all__ = [
    "CanonicalSink",
    "Connector",
    "ConnectorConfig",
    "HealthStatus",
    "SyncCursor",
    "SyncResult",
    "discover",
    "run_sync",
]
