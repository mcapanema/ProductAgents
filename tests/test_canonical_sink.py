"""The sink writes any canonical model, dispatching by type, and dedups."""

from productagents.core.models import CustomerFeedback, Initiative, SourceRef
from productagents.knowledge.repositories.sqlmodel.canonical_repository import (
    CanonicalRepository,
)
from productagents.knowledge.sink import DbCanonicalSink
from tests.storage_fixtures import memory_store, sample_models


async def test_write_persists_a_single_model():
    initiative = Initiative(title="Add SSO", description="d")
    async with memory_store() as (sessionmaker, _engine):
        sink = DbCanonicalSink(sessionmaker)
        await sink.write(initiative)
        async with sessionmaker() as session:
            fetched = await CanonicalRepository(session, Initiative).get(
                str(initiative.id)
            )
    assert fetched == initiative


async def test_write_many_dispatches_by_type():
    models = sample_models()
    async with memory_store() as (sessionmaker, _engine):
        sink = DbCanonicalSink(sessionmaker)
        await sink.write_many(models)
        async with sessionmaker() as session:
            initiatives = await CanonicalRepository(session, Initiative).list()
            feedback = await CanonicalRepository(session, CustomerFeedback).list()
    assert len(initiatives) == 1
    assert len(feedback) == 1


async def test_write_is_idempotent_on_resync():
    src = SourceRef(connector="github", vendor_type="issue", vendor_id="GH-1")
    async with memory_store() as (sessionmaker, _engine):
        sink = DbCanonicalSink(sessionmaker)
        await sink.write(Initiative(title="t", description="d", source=src))
        await sink.write(Initiative(title="t", description="d2", source=src))
        async with sessionmaker() as session:
            rows = await CanonicalRepository(session, Initiative).list()
    assert len(rows) == 1
    assert rows[0].description == "d2"
