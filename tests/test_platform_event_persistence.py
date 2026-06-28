# tests/test_platform_event_persistence.py
import asyncio
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.memory import store as store_mod
from productagents.memory.event_store import EventStore
from productagents.platform.decision_service import DecisionService


async def _collect(stream):
    return [e async for e in stream]


@pytest.fixture
async def event_store_io():
    """A shared-engine EventStore opener plus a reader over the same DB."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await store_mod.create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def opener():
        async with maker() as s:
            yield EventStore(s)

    yield opener
    await engine.dispose()


async def test_run_persists_full_event_stream(decision_inputs, event_store_io):
    initiative, evidence_spec, context_opener = decision_inputs
    service = DecisionService(context_opener, event_store_opener=event_store_io)

    session, stream = service.start_session(initiative, evidence_spec)
    await _collect(stream)
    await asyncio.gather(*list(service._tasks))  # let the persist task drain

    async with event_store_io() as store:
        events = await store.events(session.id)
        header = await store.get_session(session.id)

    assert events[0]["event_type"] == "SessionStarted"
    assert events[-1]["event_type"] == "SessionFinished"
    assert [e["seq"] for e in events] == sorted(e["seq"] for e in events)
    assert header["status"] == "finished"


async def test_persistence_is_off_when_no_opener(decision_inputs):
    """No event_store_opener → no persist task spawned, run still completes."""
    initiative, evidence_spec, context_opener = decision_inputs
    service = DecisionService(context_opener)  # opener omitted
    session, stream = service.start_session(initiative, evidence_spec)
    received = await _collect(stream)
    assert received[-1].__class__.__name__ == "SessionFinished"
    assert session.status == "finished"
