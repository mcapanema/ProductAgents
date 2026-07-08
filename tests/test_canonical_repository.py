"""Repository contract: every canonical type persists, reads back, and dedups."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from productagents.core.models import CustomerFeedback, Initiative, SourceRef
from productagents.knowledge.repositories.sqlmodel.canonical_repository import (
    CanonicalRepository,
)
from productagents.knowledge.repositories.sqlmodel.tables import CanonicalRecord
from tests.storage_fixtures import memory_store, sample_models


@pytest.mark.parametrize("model", sample_models(), ids=lambda m: type(m).__name__)
async def test_upsert_then_get_round_trips(model):
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        repo = CanonicalRepository(session, type(model))
        await repo.upsert(model)
        fetched = await repo.get(str(model.id))
    assert fetched == model


async def test_get_returns_none_for_unknown_id():
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        repo = CanonicalRepository(session, Initiative)
        assert await repo.get("does-not-exist") is None


async def test_get_is_type_scoped():
    # A row of a different model_type must not surface through another repo.
    feedback = CustomerFeedback(body="hi")
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        await CanonicalRepository(session, CustomerFeedback).upsert(feedback)
        wrong = CanonicalRepository(session, Initiative)
        assert await wrong.get(str(feedback.id)) is None


async def test_list_returns_only_that_type():
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        await CanonicalRepository(session, Initiative).upsert(
            Initiative(title="A", description="a")
        )
        await CanonicalRepository(session, Initiative).upsert(
            Initiative(title="B", description="b")
        )
        await CanonicalRepository(session, CustomerFeedback).upsert(
            CustomerFeedback(body="c")
        )
        initiatives = await CanonicalRepository(session, Initiative).list()
    titles = sorted(i.title for i in initiatives)
    assert titles == ["A", "B"]


async def test_manual_upsert_updates_in_place_by_id():
    initiative = Initiative(title="v1", description="d")
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        repo = CanonicalRepository(session, Initiative)
        await repo.upsert(initiative)
        updated = initiative.model_copy(update={"title": "v2"})
        await repo.upsert(updated)
        rows = await repo.list()
        fetched = await repo.get(str(initiative.id))
    assert len(rows) == 1  # updated in place, not duplicated
    assert fetched is not None
    assert fetched.title == "v2"


async def test_vendor_upsert_preserves_original_platform_id():
    # Two syncs of the same vendor record (fresh ids each time) must collapse to
    # one row and keep the FIRST platform id stable.
    src = SourceRef(connector="zendesk", vendor_type="ticket", vendor_id="Z-9")
    first = CustomerFeedback(body="sync 1", source=src)
    second = CustomerFeedback(body="sync 2", source=src)  # different .id
    assert first.id != second.id
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        repo = CanonicalRepository(session, CustomerFeedback)
        await repo.upsert(first)
        returned = await repo.upsert(second)
        rows = await repo.list()
    assert len(rows) == 1
    assert returned.id == first.id  # original id wins
    assert returned.body == "sync 2"  # newer payload wins
    assert returned.ingested_at == first.ingested_at  # first-seen time is stable


async def test_canonical_records_isolated_per_workspace():
    src = SourceRef(connector="zendesk", vendor_type="ticket", vendor_id="1")
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        a = CanonicalRepository(session, CustomerFeedback, workspace="a")
        b = CanonicalRepository(session, CustomerFeedback, workspace="b")
        fa = await a.upsert(CustomerFeedback(body="hi", source=src))
        # same vendor identity, other workspace — allowed
        await b.upsert(CustomerFeedback(body="hi", source=src))
        assert [m.id for m in await a.list()] == [fa.id]
        assert await a.get(str(fa.id)) is not None
        only_b = await b.list()
    assert len(only_b) == 1
    assert only_b[0].id != fa.id


async def test_upsert_dedups_within_workspace_only():
    src = SourceRef(connector="zendesk", vendor_type="ticket", vendor_id="7")
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        a = CanonicalRepository(session, CustomerFeedback, workspace="a")
        first = await a.upsert(CustomerFeedback(body="v1", source=src))
        again = await a.upsert(CustomerFeedback(body="v2", source=src))
        assert again.id == first.id  # stable platform id within the workspace
        assert len(await a.list()) == 1


async def test_rename_workspace_moves_canonical_and_cursor_rows():
    from productagents.knowledge import rename_workspace
    from productagents.knowledge.sync_state import SyncStateStore

    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        repo_old = CanonicalRepository(session, CustomerFeedback, workspace="old")
        repo_by = CanonicalRepository(session, CustomerFeedback, workspace="bystander")
        kept = await repo_old.upsert(CustomerFeedback(body="feedback1"))
        await repo_by.upsert(CustomerFeedback(body="feedback2"))
        await SyncStateStore(session, workspace="old").save("github", "cur")

        await rename_workspace(session, "old", "new")
        await session.commit()

        repo_new = CanonicalRepository(session, CustomerFeedback, workspace="new")
        assert [m.id for m in await repo_new.list()] == [kept.id]
        assert (
            await CanonicalRepository(session, CustomerFeedback, workspace="old").list()
            == []
        )
        assert len(await repo_by.list()) == 1
        assert await SyncStateStore(session, workspace="new").cursors() == {
            "github": "cur"
        }
        assert await SyncStateStore(session, workspace="old").cursors() == {}


async def test_canonical_record_ingested_and_updated_at_are_tz_aware():
    # ingested_at/updated_at are tz-aware by default (CanonicalModel._utcnow());
    # the column must preserve that, not silently drop the offset (regression
    # guard for the naive-DateTime bug fixed by migration 0004). Read the raw
    # CanonicalRecord row directly — CanonicalRepository.get()/from_row() only
    # ever validates the JSON `payload` blob and never touches these two SQL
    # columns, so round-tripping through the repository proves nothing about
    # them (that was the vacuous version of this test).
    async with memory_store() as (sessionmaker, _engine):
        async with sessionmaker() as session:
            created = await CanonicalRepository(session, CustomerFeedback).upsert(
                CustomerFeedback(body="hello")
            )
        async with sessionmaker() as session:
            row = await session.get(CanonicalRecord, str(created.id))
    assert row is not None
    assert row.ingested_at.tzinfo is not None
    assert row.updated_at.tzinfo is not None


async def test_upsert_retries_as_update_on_integrity_error(monkeypatch):
    # Simulate the SELECT-then-INSERT race: _find_existing misses, another writer
    # has already inserted the same vendor identity, so our INSERT hits the unique
    # constraint. The upsert must roll back and resolve to an update, not abort.
    from productagents.core.models import CustomerFeedback, SourceRef

    src = SourceRef(connector="zendesk", vendor_type="ticket", vendor_id="RACE-1")
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        repo = CanonicalRepository(session, CustomerFeedback)
        await repo.upsert(
            CustomerFeedback(body="winner", source=src)
        )  # the racing insert

        calls = {"n": 0}
        real_find = repo._find_existing

        async def flaky_find(incoming):
            calls["n"] += 1
            if calls["n"] == 1:
                return None  # pretend we didn't see the existing row -> forces INSERT
            return await real_find(incoming)

        monkeypatch.setattr(repo, "_find_existing", flaky_find)
        returned = await repo.upsert(CustomerFeedback(body="loser", source=src))
        rows = await repo.list()

    assert calls["n"] == 2  # missed, conflicted, re-found on retry
    assert len(rows) == 1  # collapsed to one row, no duplicate
    assert returned.body == "loser"  # newer payload applied via the update path


async def test_utc_datetime_normalizes_non_utc_offset_before_storage():
    # A non-UTC-aware datetime (+05:00) must be converted to the equivalent UTC
    # instant before SQLite stores it, not just tagged with +00:00 in place —
    # SQLite keeps only the wall-clock digits, so tagging-without-converting
    # would silently round-trip the wrong instant (regression guard for the
    # bug in UTCDateTime.process_bind_param).
    offset_dt = datetime(2026, 1, 1, 10, 0, tzinfo=timezone(timedelta(hours=5)))
    async with memory_store() as (sessionmaker, _engine):
        async with sessionmaker() as session:
            created = await CanonicalRepository(session, CustomerFeedback).upsert(
                CustomerFeedback(body="hello")
            )
            row = await session.get(CanonicalRecord, str(created.id))
            row.ingested_at = offset_dt
            await session.commit()
        async with sessionmaker() as session:
            row = await session.get(CanonicalRecord, str(created.id))
    assert row is not None
    assert row.ingested_at == datetime(2026, 1, 1, 5, 0, tzinfo=UTC)


async def test_apply_update_legacy_row_without_ingested_at():
    """N18: _apply_update gracefully handles legacy rows with no ingested_at key."""
    src = SourceRef(connector="github", vendor_type="issue", vendor_id="123")
    first = CustomerFeedback(body="v1", source=src)
    async with memory_store() as (sessionmaker, _engine):
        # Create an initial record with synced source
        async with sessionmaker() as session:
            repo = CanonicalRepository(session, CustomerFeedback)
            created = await repo.upsert(first)
        # Simulate a legacy row by removing ingested_at from payload
        async with sessionmaker() as session:
            row = await session.get(CanonicalRecord, str(created.id))
            row.payload = {"body": "v1"}  # No ingested_at key
            await session.commit()
        # Update should succeed and handle missing ingested_at gracefully
        second = CustomerFeedback(body="v2", source=src)
        async with sessionmaker() as session:
            repo = CanonicalRepository(session, CustomerFeedback)
            updated = await repo.upsert(second)
            second_ingested_at = second.ingested_at
        # Verify the fallback used incoming.ingested_at, not a fresh timestamp
        assert updated.id == created.id
        assert updated.body == "v2"
        assert updated.ingested_at == second_ingested_at
        # Third upsert confirms the value is stable, not re-generated
        third = CustomerFeedback(body="v3", source=src)
        async with sessionmaker() as session:
            repo = CanonicalRepository(session, CustomerFeedback)
            updated_again = await repo.upsert(third)
    assert updated_again.ingested_at == second_ingested_at
