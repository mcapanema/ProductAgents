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


async def test_save_retries_on_integrity_error(monkeypatch):
    # Two writers racing the first save of the same connector_key: one wins the
    # INSERT, the loser's merge hits the PK and must retry-as-update, not abort.
    from productagents.knowledge.sync_state import SyncStateStore
    from tests.storage_fixtures import memory_store

    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        store = SyncStateStore(session)
        await store.save("github", "cur-1")

        original_commit = session.commit
        calls = {"n": 0}

        async def flaky_commit():
            calls["n"] += 1
            if calls["n"] == 1:
                raise __import__("sqlalchemy").exc.IntegrityError("x", {}, Exception())
            return await original_commit()

        monkeypatch.setattr(session, "commit", flaky_commit)
        await store.save("github", "cur-2")  # must survive the injected conflict
        monkeypatch.setattr(session, "commit", original_commit)

        assert await store.cursors() == {"github": "cur-2"}
    assert calls["n"] == 2


async def test_sync_state_updated_at_is_tz_aware():
    from productagents.knowledge.repositories.sqlmodel.tables import SyncStateRecord
    from productagents.knowledge.sync_state import SyncStateStore

    # updated_at is written as datetime.now(UTC); the column must preserve the
    # offset, not silently drop it (regression guard for the naive-DateTime bug
    # fixed by migration 0004). Read the raw SyncStateRecord row directly — this
    # is exactly the column last_synced() calls .isoformat() on, no JSON-payload
    # indirection to hide behind.
    async with memory_store() as (sessionmaker, _engine):
        async with sessionmaker() as session:
            await SyncStateStore(session).save("github", "cursor-1")
        async with sessionmaker() as session:
            row = await session.get(SyncStateRecord, ("default", "github"))
    assert row is not None
    assert row.updated_at.tzinfo is not None
