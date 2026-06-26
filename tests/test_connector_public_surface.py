"""The package's public import surface — the one consumers should depend on."""

import productagents.connectors as connectors


def test_public_surface():
    for name in (
        "Connector",
        "ConnectorConfig",
        "CanonicalSink",
        "SyncCursor",
        "SyncResult",
        "HealthStatus",
        "run_sync",
        "discover",
    ):
        assert hasattr(connectors, name), name
