"""open_workflow_store yields a workspace-scoped WorkflowDefinitionStore."""

from productagents.agents.default_workflow import default_definition
from productagents.memory.store import create_all
from productagents.platform import context as ctx


async def test_open_workflow_store_roundtrips(tmp_path, monkeypatch):
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await create_all(engine)
    monkeypatch.setattr(ctx, "get_engine", lambda: engine)

    async with ctx.open_workflow_store(workspace="default") as store:
        await store.ensure_default(default_definition())
    async with ctx.open_workflow_store(workspace="default") as store:
        assert [d.name for d in await store.list()] == ["evaluate_initiative"]
