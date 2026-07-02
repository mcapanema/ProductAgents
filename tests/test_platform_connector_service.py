"""Tests for ConnectorService — delegates to platform.connectors functions."""

import pytest

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


async def test_config_list_includes_schema_and_current_block(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from productagents.memory.store import create_all as memory_create_all
    from productagents.memory.workspace_state import ConnectorConfigStore

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await memory_create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    from productagents.connectors.github.connector import GitHubConnector
    from productagents.platform.connector_service import ConnectorService

    svc = ConnectorService(engine=engine, env_path=str(tmp_path / ".env"))
    async with maker() as session:
        await ConnectorConfigStore(session).set(
            "github", {"owner": "acme", "repo": "widgets", "token_env": "GH_TOKEN"}
        )
    entries = await svc.config_list(registry={"github": GitHubConnector})
    (gh,) = entries
    assert gh["connector"] == "github"
    assert gh["installed"] is True
    assert gh["config"]["owner"] == "acme"
    assert "owner" in gh["schema"]["properties"]


async def test_config_save_validates_writes_and_persists_secret(tmp_path, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from productagents.memory.store import create_all as memory_create_all
    from productagents.memory.workspace_state import ConnectorConfigStore

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await memory_create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    from productagents.connectors.github.connector import GitHubConnector

    monkeypatch.delenv("GH_TOKEN", raising=False)
    svc = ConnectorService(engine=engine, env_path=str(tmp_path / ".env"))
    registry = {"github": GitHubConnector}

    # Enabled block referencing an unset secret and no secret supplied -> rejected.
    block = {
        "owner": "acme",
        "repo": "widgets",
        "token_env": "GH_TOKEN",
        "enabled": True,
    }
    with pytest.raises(ValueError, match="GH_TOKEN"):
        await svc.config_save("github", block, registry=registry)

    # Supplying the secret makes it valid; secret goes to .env, never the DB.
    entry = await svc.config_save(
        "github", block, secrets={"GH_TOKEN": "ghp_x"}, registry=registry
    )
    assert entry["config"]["owner"] == "acme"
    assert "ghp_x" in (tmp_path / ".env").read_text()
    async with maker() as session:
        assert "ghp_x" not in str(await ConnectorConfigStore(session).all())

    # A secret var NOT referenced by any *_env field is rejected (no arbitrary
    # env writes).
    with pytest.raises(ValueError, match="not referenced"):
        await svc.config_save(
            "github", block, secrets={"PATH": "evil"}, registry=registry
        )

    # Disabled blocks save without validation (drafting).
    await svc.config_save("github", {"enabled": False, "owner": "x"}, registry=registry)
