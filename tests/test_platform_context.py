"""Workspace threading through the platform context openers."""

from productagents.knowledge.repositories.sqlmodel.engine import make_engine
from productagents.memory.store import create_all
from productagents.platform.context import (
    make_recorder,
    open_decision_store,
    open_event_store,
)


async def test_openers_and_recorder_are_workspace_scoped(make_decision_record):
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    await create_all(engine)

    rec_a = make_recorder(workspace="a", engine=engine)
    await rec_a(make_decision_record("d-a"))
    rec_b = make_recorder(workspace="b", engine=engine)
    await rec_b(make_decision_record("d-b"))

    async with open_decision_store(workspace="a", engine=engine) as store:
        assert [d.decision_id for d in await store.decisions()] == ["d-a"]

    async with open_event_store(workspace="a", engine=engine) as events:
        await events.start_session("s-a", "wf", "running", "2026-01-01T00:00:00+00:00")
    async with open_event_store(workspace="b", engine=engine) as events:
        assert await events.sessions() == []
