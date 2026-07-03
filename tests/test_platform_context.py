"""Workspace threading through the platform context openers."""

from productagents.knowledge.repositories.sqlmodel.engine import (
    make_engine,
    make_sessionmaker,
)
from productagents.memory.store import create_all
from productagents.platform.context import (
    make_recorder,
    open_agent_context,
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


async def test_agent_context_prompts_are_workspace_scoped(monkeypatch, tmp_path):
    """Live-run nodes must see per-workspace prompt overrides, not the raw dir."""
    override = tmp_path / "team-a" / "customer_research"
    override.mkdir(parents=True)
    (override / "0001.txt").write_text("team-a override", encoding="utf-8")
    monkeypatch.setenv("PRODUCTAGENTS_PROMPTS_DIR", str(tmp_path))

    engine = make_engine("sqlite+aiosqlite:///:memory:")
    await create_all(engine)
    maker = make_sessionmaker(engine)

    async with open_agent_context(
        None, workspace="team-a", session_factory=maker
    ) as ctx:
        assert ctx.prompts.get("customer_research") == "team-a override"
    async with open_agent_context(
        None, workspace="team-b", session_factory=maker
    ) as ctx:
        assert ctx.prompts.active_version("customer_research") == 0
