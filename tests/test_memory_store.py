import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.core.models import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)
from productagents.memory import store as store_mod
from productagents.memory.store import DecisionStore
from productagents.memory.tables import Base


def _engine():
    return create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


async def test_memory_tables_are_created():
    engine = _engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    assert {"memory_decision", "memory_outcome"} <= set(names)


def _decision(decision_id="d1", title="Add enterprise SSO"):
    return DecisionRecord(
        decision_id=decision_id,
        initiative=Initiative(title=title, description="desc"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


@pytest.fixture
async def session():
    from sqlalchemy.ext.asyncio import async_sessionmaker

    engine = _engine()
    await store_mod.create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_record_and_read_decision_round_trips(session):
    s = DecisionStore(session)
    await s.record(_decision(), [0.1, 0.2, 0.3])
    got = await s.decisions()
    assert len(got) == 1
    assert got[0].initiative.title == "Add enterprise SSO"
    assert got[0].recommendation.confidence == 0.7
    assert await s.embeddings() == {"d1": [0.1, 0.2, 0.3]}


async def test_record_decision_upserts_on_id(session):
    s = DecisionStore(session)
    await s.record(_decision(title="v1"), [0.0])
    await s.record(_decision(title="v2"), [1.0])
    got = await s.decisions()
    assert len(got) == 1
    assert got[0].initiative.title == "v2"


async def test_outcomes_round_trip(session):
    s = DecisionStore(session)
    await s.record_outcome(
        OutcomeRecord(
            decision_id="d1",
            actual_outcomes=["shipped late"],
            prediction_accuracy=0.5,
            lessons_learned=["SSO takes longer"],
            reflected_at="2026-06-20T00:00:00+00:00",
        )
    )
    got = await s.outcomes()
    assert len(got) == 1
    assert got[0].lessons_learned == ["SSO takes longer"]


async def test_decisions_are_isolated_per_workspace(session):
    a = DecisionStore(session, "a")
    b = DecisionStore(session, "b")
    await a.record(_decision("da"), [0.1])
    await b.record(_decision("db"), [0.2])

    assert [d.decision_id for d in await a.decisions()] == ["da"]
    assert list((await a.embeddings()).keys()) == ["da"]
    await a.record_outcome(
        OutcomeRecord(
            decision_id="da",
            actual_outcomes=["shipped"],
            prediction_accuracy=0.8,
            lessons_learned=["SSO was worth it"],
            reflected_at="2026-06-20T00:00:00+00:00",
        )
    )
    await b.record_outcome(
        OutcomeRecord(
            decision_id="db",
            actual_outcomes=["delayed"],
            prediction_accuracy=0.5,
            lessons_learned=["delayed"],
            reflected_at="2026-06-20T00:00:00+00:00",
        )
    )
    assert [o.decision_id for o in await a.outcomes()] == ["da"]


async def test_commit_rolls_back_so_the_session_stays_usable(monkeypatch):
    # A failed commit must roll the session back, not poison it — the next write
    # on the same session must still succeed (no PendingRollbackError).
    from productagents.memory._tx import commit
    from tests.storage_fixtures import memory_store

    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        from sqlalchemy import text

        # raw-sql-test
        await session.execute(text("CREATE TABLE probe (x INTEGER PRIMARY KEY)"))
        await session.execute(text("INSERT INTO probe VALUES (1)"))
        await commit(session)

        real_commit = session.commit

        async def boom():
            raise RuntimeError("commit failed")

        monkeypatch.setattr(session, "commit", boom)
        with pytest.raises(RuntimeError):
            await commit(session)
        monkeypatch.setattr(session, "commit", real_commit)

        # Session recovered: a fresh insert commits fine.
        # raw-sql-test
        await session.execute(text("INSERT INTO probe VALUES (2)"))
        await commit(session)
        rows = (await session.execute(text("SELECT x FROM probe ORDER BY x"))).all()
    assert rows == [(1,), (2,)]
