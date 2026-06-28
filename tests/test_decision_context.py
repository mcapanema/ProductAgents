"""Decision-context: core.models.decision tests + app.decision_context tests."""

from productagents.core.models.decision import DecisionRecord, Recommendation
from productagents.core.models.planning import Initiative

# ---------------------------------------------------------------------------
# DB-backed recorder / reader round-trip (Task 9)
# ---------------------------------------------------------------------------


async def test_recorder_then_reader_round_trip():
    from productagents.core.models import OutcomeRecord  # noqa: F401
    from productagents.knowledge.repositories.sqlmodel.engine import make_engine
    from productagents.memory import store as store_mod
    from productagents.platform.context import make_decision_reader, make_recorder

    def _decision():
        return DecisionRecord(
            decision_id="d1",
            initiative=Initiative(title="Add SSO", description="enterprise auth"),
            recommendation=Recommendation(
                recommendation="Build",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            ),
            reports=[],
            timestamp="2026-06-19T12:00:00+00:00",
        )

    engine = make_engine("sqlite+aiosqlite://")
    await store_mod.create_all(engine)
    record = make_recorder(engine=engine)
    read = make_decision_reader(engine=engine)
    await record(_decision())
    decisions = await read()
    assert [d.decision_id for d in decisions] == ["d1"]
    await engine.dispose()


async def test_outcome_recorder_persists():
    from productagents.core.models import OutcomeRecord
    from productagents.knowledge.repositories.sqlmodel.engine import make_engine
    from productagents.memory import store as store_mod
    from productagents.platform.context import (
        make_decision_reader,
        make_outcome_recorder,
        make_recorder,
    )

    def _decision():
        return DecisionRecord(
            decision_id="d1",
            initiative=Initiative(title="Add SSO", description="enterprise auth"),
            recommendation=Recommendation(
                recommendation="Build",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            ),
            reports=[],
            timestamp="2026-06-19T12:00:00+00:00",
        )

    engine = make_engine("sqlite+aiosqlite://")
    await store_mod.create_all(engine)
    record = make_recorder(engine=engine)
    record_outcome = make_outcome_recorder(engine=engine)
    read = make_decision_reader(engine=engine)
    await record(_decision())
    await record_outcome(
        OutcomeRecord(
            decision_id="d1",
            actual_outcomes=["ok"],
            prediction_accuracy=0.8,
            lessons_learned=["lesson"],
            reflected_at="2026-06-20T00:00:00+00:00",
        )
    )
    decisions = await read()
    assert decisions
    assert decisions[0].decision_id == "d1"
    await engine.dispose()


def test_decision_record_uses_planning_initiative():
    rec = DecisionRecord(
        initiative=Initiative(title="Add SSO", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.8,
            rationale="strong demand",
            expected_outcomes=["enterprise unblock"],
        ),
        reports=[],
        timestamp="2026-06-23T12:00:00+00:00",
    )
    assert isinstance(rec.initiative, Initiative)
    assert DecisionRecord.model_validate_json(rec.model_dump_json()) == rec


def test_decision_record_generates_id_by_default():
    def make() -> DecisionRecord:
        return DecisionRecord(
            initiative=Initiative(title="t", description="d"),
            recommendation=Recommendation(
                recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
            ),
            reports=[],
            timestamp="2026-06-23T12:00:00+00:00",
        )

    assert make().decision_id != make().decision_id


# ---------------------------------------------------------------------------
# app.decision_context boundary tests
# ---------------------------------------------------------------------------


async def test_open_agent_context_wires_store_feedback():
    from productagents.core.models import CustomerFeedback
    from productagents.knowledge import DbCanonicalSink, FeedbackQuery
    from productagents.platform.context import open_agent_context
    from tests.storage_fixtures import memory_store

    async with memory_store() as (sessionmaker, _engine):
        await DbCanonicalSink(sessionmaker).write(
            CustomerFeedback(body="STORE feedback")
        )
        async with open_agent_context("model", session_factory=sessionmaker) as ctx:
            page = await ctx.feedback.search(FeedbackQuery())
            assert [f.body for f in page.items] == ["STORE feedback"]
            assert ctx.model == "model"


async def test_open_agent_context_returns_agent_context():
    from productagents.agents.context import AgentContext
    from productagents.platform.context import open_agent_context
    from tests.storage_fixtures import memory_store

    async with (
        memory_store() as (sessionmaker, _engine),
        open_agent_context("my-model", session_factory=sessionmaker) as ctx,
    ):
        assert isinstance(ctx, AgentContext)
        assert ctx.model == "my-model"
