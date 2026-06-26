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
from tests.memory_fakes import FakeEmbedder


def _decision(decision_id, title, desc):
    return DecisionRecord(
        decision_id=decision_id,
        initiative=Initiative(title=title, description=desc),
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
async def store():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await store_mod.create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield DecisionStore(s)
    await engine.dispose()


async def test_record_then_lexical_recall(store):
    embedder = FakeEmbedder({}, default=[0.0])
    svc = LearningService(store, embedder)
    await svc.record_decision(_decision("d1", "Add enterprise SSO login", "auth"))
    await svc.record_outcome(
        OutcomeRecord(
            decision_id="d1",
            actual_outcomes=["late"],
            prediction_accuracy=0.5,
            lessons_learned=["SSO integrations take longer than predicted"],
            reflected_at="2026-06-20T00:00:00+00:00",
        )
    )
    lessons = await svc.relevant_lessons(Initiative(title="Add SSO", description="SSO"))
    assert any("take longer than predicted" in line for line in lessons)


async def test_semantic_recall_without_lexical_overlap(store):
    # Past decision and query share NO tokens, but the embedder maps both to the
    # same vector — the service must surface it via the semantic path.
    embedder = FakeEmbedder(
        {
            "Quarterly billing migration ledger reconciliation": [1.0, 0.0],
            "Realtime fraud scoring risk engine": [1.0, 0.0],
        },
        default=[0.0, 1.0],
    )
    svc = LearningService(store, embedder)
    await svc.record_decision(
        _decision("d1", "Quarterly billing migration", "ledger reconciliation")
    )
    lessons = await svc.relevant_lessons(
        Initiative(title="Realtime fraud scoring", description="risk engine")
    )
    assert any("Quarterly billing migration" in line for line in lessons)


async def test_relevant_lessons_empty_without_history(store):
    svc = LearningService(store, FakeEmbedder({}, default=[0.0]))
    assert await svc.relevant_lessons(Initiative(title="X", description="y")) == []
