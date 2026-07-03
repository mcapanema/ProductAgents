"""The three workspace-state stores: plain KV/JSON rows, session-injected."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.memory.store import create_all
from productagents.memory.workspace_state import (
    ConnectorConfigStore,
    PreferenceStore,
    WorkspaceConfigStore,
    WorkspaceRegistry,
)


@pytest.fixture
async def sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await create_all(engine)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_workspace_config_roundtrip_and_upsert(sessionmaker):
    async with sessionmaker() as session:
        store = WorkspaceConfigStore(session)
        assert await store.all() == {}
        await store.set("debate_rounds", "3")
        await store.set("debate_rounds", "4")  # upsert, not duplicate
        await store.set("model", "anthropic:m")
        assert await store.all() == {"debate_rounds": "4", "model": "anthropic:m"}


async def test_workspace_config_delete(sessionmaker):
    async with sessionmaker() as session:
        store = WorkspaceConfigStore(session)
        await store.set("model", "x")
        await store.delete("model")
        await store.delete("model")  # deleting a missing key is a no-op
        assert await store.all() == {}


async def test_connector_config_roundtrip(sessionmaker):
    async with sessionmaker() as session:
        store = ConnectorConfigStore(session)
        assert await store.all() == {}
        block = {"owner": "acme", "repo": "widgets", "token_env": "GH", "enabled": True}
        await store.set("github", block)
        await store.set("github", {**block, "enabled": False})  # upsert
        assert (await store.all())["github"]["enabled"] is False


async def test_preference_roundtrip(sessionmaker):
    async with sessionmaker() as session:
        store = PreferenceStore(session)
        assert await store.get("theme") is None
        await store.set("theme", "dark")
        assert await store.get("theme") == "dark"
        assert await store.all() == {"theme": "dark"}


async def test_config_store_isolated_per_workspace(sessionmaker):
    async with sessionmaker() as session:
        a = WorkspaceConfigStore(session, "a")
        b = WorkspaceConfigStore(session, "b")
        await a.set("model", "anthropic:x")
        await b.set("model", "openai:y")
        assert await a.all() == {"model": "anthropic:x"}
        await a.delete("model")
        assert await a.all() == {}
        assert await b.all() == {"model": "openai:y"}


async def test_connector_store_isolated_per_workspace(sessionmaker):
    async with sessionmaker() as session:
        a = ConnectorConfigStore(session, "a")
        b = ConnectorConfigStore(session, "b")
        await a.set("github", {"repo": "org/a"})
        await b.set("github", {"repo": "org/b"})
        assert await a.all() == {"github": {"repo": "org/a"}}


async def test_registry_create_list_ensure(sessionmaker):
    async with sessionmaker() as session:
        reg = WorkspaceRegistry(session)
        await reg.ensure("default")
        await reg.ensure("default")  # idempotent
        created = await reg.create("acme")
        assert created["name"] == "acme"
        assert created["created_at"]
        with pytest.raises(ValueError, match="workspace already exists"):
            await reg.create("acme")
        assert [w["name"] for w in await reg.list()] == ["acme", "default"]
        assert await reg.get("nope") is None
