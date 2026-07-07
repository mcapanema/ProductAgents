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


async def test_sessions_are_isolated_per_workspace():
    """Sessions are scoped to workspace, but events are globally keyed by session_id."""
    engine = _engine()
    await store_mod.create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        a = EventStore(session, "a")
        b = EventStore(session, "b")
        await a.start_session("s-a", "wf", "running", "2026-01-01T00:00:00+00:00")
        await b.start_session("s-b", "wf", "running", "2026-01-02T00:00:00+00:00")
        assert [r["id"] for r in await a.sessions()] == ["s-a"]
        # events are keyed by globally-unique session_id — no workspace column
        await b.append("s-b", 0, "SessionStarted", "t", {})
        assert await a.events("s-b") == [
            {
                "session_id": "s-b",
                "seq": 0,
                "event_type": "SessionStarted",
                "ts": "t",
                "payload": {},
            }
        ]
    await engine.dispose()


async def test_append_tolerates_duplicate_seq(store):
    # A retried append at the same (session_id, seq) must be a no-op, not a dup
    # row and not an aborted run — the unique constraint + IntegrityError
    # tolerance make appends idempotent.
    await store.start_session("s1", "wf", "running", "2026-01-01T00:00:00+00:00")
    await store.append("s1", 0, "Started", "2026-01-01T00:00:00+00:00", {})
    await store.append("s1", 0, "Started", "2026-01-01T00:00:00+00:00", {})  # retry
    events = await store.events("s1")
    assert len(events) == 1  # deduped by the unique constraint, run still alive

    # The session must stay usable afterward for a genuinely new event.
    await store.append("s1", 1, "NodeComplete", "2026-01-01T00:00:01+00:00", {})
    events = await store.events("s1")
    assert len(events) == 2
    assert {e["seq"] for e in events} == {0, 1}


async def test_start_session_commit_is_rollback_guarded(store, monkeypatch):
    # If the commit fails, EventStore must roll back rather than leave the shared
    # session poisoned for the rest of the run.
    boom_count = {"n": 0}
    real_commit = store._session.commit

    async def boom():
        boom_count["n"] += 1
        raise RuntimeError("commit failed")

    monkeypatch.setattr(store._session, "commit", boom)
    with pytest.raises(RuntimeError):
        await store.start_session("s1", "wf", "running", "2026-01-01T00:00:00+00:00")
    monkeypatch.setattr(store._session, "commit", real_commit)
    # Session is usable again: a real start_session now succeeds.
    await store.start_session("s2", "wf", "running", "2026-01-02T00:00:00+00:00")
    assert {s["id"] for s in await store.sessions()} == {"s2"}
