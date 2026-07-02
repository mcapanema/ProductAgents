"""Tests for ConnectorService — delegates to platform.connectors functions."""

from productagents.platform.connector_service import ConnectorService


async def test_connector_service_health_delegates(monkeypatch):
    sentinel = ["ok"]

    async def fake_health(*args, **kwargs):
        return sentinel

    monkeypatch.setattr(
        "productagents.platform.connectors.check_connector_health", fake_health
    )
    service = ConnectorService()
    assert await service.health() is sentinel


async def test_connector_service_sync_delegates(monkeypatch):
    from productagents.platform.connectors import SyncReport

    expected = SyncReport()

    async def fake_sync(*args, **kwargs):
        return expected

    monkeypatch.setattr(
        "productagents.platform.connectors.run_connector_sync", fake_sync
    )
    service = ConnectorService()
    assert await service.sync() is expected


async def test_connector_service_plan_delegates(monkeypatch):
    sentinel = object()

    async def fake_plan(*args, **kwargs):
        return sentinel

    monkeypatch.setattr(
        "productagents.platform.connectors.connector_plan",
        fake_plan,
    )
    assert await ConnectorService().plan() is sentinel
