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
