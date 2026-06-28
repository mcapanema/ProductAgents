# tests/test_platform_session_service.py
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.memory import store as store_mod
from productagents.memory.event_store import EventStore
from productagents.platform import events as ev
from productagents.platform.serialization import serialize_event
from productagents.platform.session import Session
from productagents.platform.session_service import SessionService


@pytest.fixture
async def populated():
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

    async with opener() as store:
        await store.start_session(
            "sess1", "evaluate_initiative", "running", "2026-06-28T00:00:00+00:00"
        )
        for e in [
            ev.SessionStarted(
                session_id="sess1", seq=0, workflow="evaluate_initiative"
            ),
            ev.NodeProgress(
                session_id="sess1", seq=1, node="market", message="thinking"
            ),
        ]:
            etype, payload = serialize_event(e)
            await store.append("sess1", e.seq, etype, e.ts.isoformat(), payload)
        await store.update_status("sess1", "finished")

    yield opener
    await engine.dispose()


async def test_list_returns_session_objects(populated):
    service = SessionService(populated)
    sessions = await service.list()
    assert len(sessions) == 1
    assert isinstance(sessions[0], Session)
    assert sessions[0].id == "sess1"
    assert sessions[0].status == "finished"


async def test_get_unknown_session_returns_none(populated):
    service = SessionService(populated)
    assert await service.get("nope") is None


async def test_events_replays_typed_events_in_order(populated):
    service = SessionService(populated)
    events = await service.events("sess1")
    assert [type(e).__name__ for e in events] == ["SessionStarted", "NodeProgress"]
    assert isinstance(events[0], ev.SessionStarted)
    assert events[1].message == "thinking"  # ty: ignore[unresolved-attribute]
