"""WorkflowDefinitionStore — workspace-scoped CRUD + idempotent default seed."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.agents.default_workflow import default_definition
from productagents.core.models import WorkflowDefinition, WorkflowNodeDef
from productagents.memory.store import create_all
from productagents.memory.workspace_state import WorkflowDefinitionStore


@pytest.fixture
async def sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await create_all(engine)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _defn(name: str) -> WorkflowDefinition:
    return WorkflowDefinition(
        name=name,
        title=name.title(),
        nodes=[WorkflowNodeDef(id="market", kind="market")],
    )


async def test_ensure_default_is_idempotent_and_seeds_once(sessionmaker):
    async with sessionmaker() as session:
        store = WorkflowDefinitionStore(session, workspace="default")
        await store.ensure_default(default_definition())
        await store.ensure_default(default_definition())  # no-op
        rows = await store.list()
        assert [d.name for d in rows] == ["evaluate_initiative"]
        got = await store.get_default()
        assert got is not None
        assert got.name == "evaluate_initiative"


async def test_save_get_list_ordering(sessionmaker):
    async with sessionmaker() as session:
        store = WorkflowDefinitionStore(session, workspace="default")
        await store.ensure_default(default_definition())
        await store.save(_defn("beta"))
        await store.save(_defn("alpha"))
        names = [d.name for d in await store.list()]
        assert names[0] == "evaluate_initiative"  # default first
        assert names[1:] == ["alpha", "beta"]  # then alphabetical
        alpha = await store.get("alpha")
        assert alpha is not None
        assert alpha.title == "Alpha"
        assert await store.get("missing") is None


async def test_set_default_moves_the_flag(sessionmaker):
    async with sessionmaker() as session:
        store = WorkflowDefinitionStore(session, workspace="default")
        await store.ensure_default(default_definition())
        await store.save(_defn("beta"))
        await store.set_default("beta")
        new_default = await store.get_default()
        assert new_default is not None
        assert new_default.name == "beta"
        with pytest.raises(ValueError, match="no such workflow"):
            await store.set_default("ghost")


async def test_delete_rejects_builtin(sessionmaker):
    async with sessionmaker() as session:
        store = WorkflowDefinitionStore(session, workspace="default")
        await store.ensure_default(default_definition())
        with pytest.raises(ValueError, match="built-in"):
            await store.delete("evaluate_initiative")
        await store.save(_defn("beta"))
        await store.delete("beta")
        assert await store.get("beta") is None


async def test_workspace_scoping(sessionmaker):
    async with sessionmaker() as session:
        a = WorkflowDefinitionStore(session, workspace="a")
        b = WorkflowDefinitionStore(session, workspace="b")
        await a.save(_defn("only_a"))
        assert [d.name for d in await a.list()] == ["only_a"]
        assert await b.list() == []
