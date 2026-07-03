"""SyncStateStore persists per-connector cursor strings, round-trip stable."""

from tests.storage_fixtures import memory_store


async def test_cursors_empty_when_unset():
    from productagents.knowledge.sync_state import SyncStateStore

    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        assert await SyncStateStore(session).cursors() == {}


async def test_save_then_read_roundtrip():
    from productagents.knowledge.sync_state import SyncStateStore

    async with memory_store() as (sessionmaker, _engine):
        async with sessionmaker() as session:
            await SyncStateStore(session).save("github", "2026-06-26T00:00:00Z")
        async with sessionmaker() as session:
            assert await SyncStateStore(session).cursors() == {
                "github": "2026-06-26T00:00:00Z"
            }


async def test_save_is_upsert_on_connector_key():
    from productagents.knowledge.sync_state import SyncStateStore

    async with memory_store() as (sessionmaker, _engine):
        async with sessionmaker() as session:
            store = SyncStateStore(session)
            await store.save("github", "v1")
            await store.save("github", "v2")
        async with sessionmaker() as session:
            assert await SyncStateStore(session).cursors() == {"github": "v2"}


async def test_save_accepts_none_cursor():
    from productagents.knowledge.sync_state import SyncStateStore

    async with memory_store() as (sessionmaker, _engine):
        async with sessionmaker() as session:
            await SyncStateStore(session).save("github", None)
        async with sessionmaker() as session:
            assert await SyncStateStore(session).cursors() == {"github": None}


async def test_last_synced_returns_iso_timestamps():
    from productagents.knowledge.sync_state import SyncStateStore

    async with memory_store() as (sessionmaker, _engine):
        async with sessionmaker() as session:
            await SyncStateStore(session).save("github", "cursor-1")
        async with sessionmaker() as session:
            stamps = await SyncStateStore(session).last_synced()
    assert set(stamps) == {"github"}
    assert stamps["github"].startswith("20")  # ISO-8601 datetime string


async def test_cursors_isolated_per_workspace():
    from productagents.knowledge.sync_state import SyncStateStore

    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        a = SyncStateStore(session, workspace="a")
        b = SyncStateStore(session, workspace="b")
        await a.save("github", "cursor-a")
        await b.save("github", "cursor-b")
        assert await a.cursors() == {"github": "cursor-a"}
        assert list((await a.last_synced()).keys()) == ["github"]
