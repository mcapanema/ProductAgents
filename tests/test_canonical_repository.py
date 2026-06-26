"""Repository contract: every canonical type persists, reads back, and dedups."""

import pytest

from productagents.core.models import CustomerFeedback, Initiative, SourceRef
from productagents.knowledge.repositories.sqlmodel.canonical_repository import (
    CanonicalRepository,
)
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
    assert fetched.title == "v2"  # ty: ignore[unresolved-attribute]


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
