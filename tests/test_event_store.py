import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.memory import store as store_mod
from productagents.memory.event_store import EventStore
from productagents.memory.tables import Base


def _engine():
    return create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


async def test_runtime_tables_are_created():
    engine = _engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    assert {"runtime_session", "runtime_event"} <= set(names)


@pytest.fixture
async def store():
    engine = _engine()
    await store_mod.create_all(engine)  # shared Base → creates runtime_* too
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield EventStore(s)
    await engine.dispose()


async def test_start_session_then_get_and_list(store):
    await store.start_session(
        "sess1", "evaluate_initiative", "running", "2026-06-28T00:00:00+00:00"
    )
    got = await store.get_session("sess1")
    assert got == {
        "id": "sess1",
        "workflow": "evaluate_initiative",
        "status": "running",
        "created_at": "2026-06-28T00:00:00+00:00",
    }
    assert [s["id"] for s in await store.sessions()] == ["sess1"]


async def test_start_session_upserts_status(store):
    await store.start_session("sess1", "wf", "running", "2026-06-28T00:00:00+00:00")
    await store.update_status("sess1", "finished")
    assert (await store.get_session("sess1"))["status"] == "finished"


async def test_events_round_trip_in_seq_order(store):
    await store.start_session("sess1", "wf", "running", "2026-06-28T00:00:00+00:00")
    # append out of seq order; read back ordered by seq
    await store.append(
        "sess1",
        1,
        "NodeProgress",
        "2026-06-28T00:00:01+00:00",
        {"node": "market", "message": "b"},
    )
    await store.append(
        "sess1", 0, "SessionStarted", "2026-06-28T00:00:00+00:00", {"workflow": "wf"}
    )
    rows = await store.events("sess1")
    assert [r["seq"] for r in rows] == [0, 1]
    assert rows[0]["event_type"] == "SessionStarted"
    assert rows[1]["payload"] == {"node": "market", "message": "b"}


async def test_events_are_scoped_to_one_session(store):
    await store.append("a", 0, "NodeProgress", "t", {"x": 1})
    await store.append("b", 0, "NodeProgress", "t", {"x": 2})
    assert len(await store.events("a")) == 1
    assert (await store.events("a"))[0]["payload"] == {"x": 1}
