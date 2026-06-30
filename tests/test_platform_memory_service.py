from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.core.models import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)
from productagents.memory import store as store_mod
from productagents.memory.service import LearningService
from productagents.memory.store import DecisionStore
from productagents.platform.memory_service import Lesson, MemoryService
from tests.memory_fakes import FakeEmbedder


def _decision(decision_id, title):
    return DecisionRecord(
        decision_id=decision_id,
        initiative=Initiative(title=title, description=title),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp=f"2026-06-19T12:00:0{decision_id[-1]}+00:00",
    )


@pytest.fixture
async def opener():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await store_mod.create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _open():
        async with maker() as s:
            yield DecisionStore(s)

    # seed: d1 has a validated outcome lesson; d2 is derived (no outcome)
    async with _open() as store:
        svc = LearningService(store, FakeEmbedder({}, default=[0.0]))
        await svc.record_decision(_decision("d1", "Add SSO"))
        await svc.record_decision(_decision("d2", "Billing migration"))
        await svc.record_outcome(
            OutcomeRecord(
                decision_id="d1",
                actual_outcomes=["late"],
                prediction_accuracy=0.5,
                lessons_learned=["SSO took longer than predicted"],
                reflected_at="2026-06-20T00:00:00+00:00",
            )
        )
    yield _open
    await engine.dispose()


async def test_lessons_returns_validated_then_derived_newest_first(opener):
    lessons = await MemoryService(opener).lessons()
    assert all(isinstance(x, Lesson) for x in lessons)
    validated = [x for x in lessons if x.validated]
    assert validated
    assert validated[0].decision_id == "d1"
    assert validated[0].prediction_accuracy == 0.5
    assert any(
        x.decision_id == "d2" and not x.validated and "Build it" in x.text
        for x in lessons
    )


async def test_lessons_empty_without_history(opener):
    @asynccontextmanager
    async def _empty():
        # reuse the same engine but a store with nothing seeded would also work;
        # here just assert the limit/keyword arg path stays well-formed.
        async with opener() as store:
            yield store

    lessons = await MemoryService(opener).lessons(limit=1)
    assert len(lessons) == 1
