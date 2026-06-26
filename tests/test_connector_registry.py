"""Entry-point discovery of installed connectors."""

from importlib.metadata import EntryPoint

from productagents.connectors import registry
from productagents.connectors.base import (
    Connector,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.core.models import CustomerFeedback


class _Dummy(Connector):
    key = "dummy"
    produces = frozenset({CustomerFeedback})

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        return SyncResult(connector=self.key)


def test_discover_maps_key_to_class(monkeypatch):
    ep = EntryPoint(
        name="dummy",
        value="tests.test_connector_registry:_Dummy",
        group="productagents.connectors",
    )
    monkeypatch.setattr(registry, "entry_points", lambda group: [ep])

    found = registry.discover()

    assert found == {"dummy": _Dummy}


def test_discover_empty_when_no_entry_points(monkeypatch):
    monkeypatch.setattr(registry, "entry_points", lambda group: [])
    assert registry.discover() == {}
