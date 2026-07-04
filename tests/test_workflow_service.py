"""WorkflowService — DB-backed definition CRUD + run wiring (Plan 2)."""

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.memory.store import create_all
from productagents.memory.workspace_state import WorkflowDefinitionStore
from productagents.platform.workflow import WorkflowService
from tests.fakes import FakeChatModel


@pytest.fixture
async def store_opener():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def opener(*, workspace="default"):
        async with maker() as session:
            yield WorkflowDefinitionStore(session, workspace=workspace)

    yield opener
    await engine.dispose()


def _svc(store_opener):
    return WorkflowService.create(
        FakeChatModel({}), persist_events=False, store_opener=store_opener
    )


async def test_list_seeds_and_returns_default(store_opener):
    svc = _svc(store_opener)
    rows = await svc.list()
    assert [r["name"] for r in rows] == ["evaluate_initiative"]
    assert rows[0]["is_default"] is True


async def test_show_returns_topology(store_opener):
    svc = _svc(store_opener)
    await svc.list()  # seed
    detail = await svc.show("evaluate_initiative")
    assert detail["title"] == "Evaluate Initiative"
    assert any(n["id"] == "market" for n in detail["topology"]["nodes"])


async def test_create_clone_rename_delete(store_opener):
    svc = _svc(store_opener)
    await svc.list()
    made = await svc.create_workflow("roadmap", "Roadmap")
    assert made["name"] == "roadmap"
    cloned = await svc.clone("evaluate_initiative", "eval_copy")
    assert cloned["name"] == "eval_copy"
    await svc.rename("roadmap", "roadmap2")
    names = {r["name"] for r in await svc.list()}
    assert "roadmap2" in names
    assert "roadmap" not in names
    await svc.delete("roadmap2")
    assert "roadmap2" not in {r["name"] for r in await svc.list()}
    with pytest.raises(ValueError, match="built-in"):
        await svc.delete("evaluate_initiative")


async def test_save_rejects_invalid_definition(store_opener):
    svc = _svc(store_opener)
    await svc.list()
    bad = {
        "name": "broken",
        "title": "Broken",
        "nodes": [{"id": "judge", "kind": "judge"}],
        "edges": [
            {"source": "__start__", "target": "judge"},
            {"source": "judge", "target": "__end__"},
        ],
    }
    with pytest.raises(ValueError, match="recommendation"):
        await svc.save(bad)


async def test_set_default_moves_flag(store_opener):
    svc = _svc(store_opener)
    await svc.list()
    await svc.create_workflow("roadmap", "Roadmap")
    await svc.set_default("roadmap")
    rows = {r["name"]: r["is_default"] for r in await svc.list()}
    assert rows["roadmap"] is True
    assert rows["evaluate_initiative"] is False


def test_palette_lists_placeable_kinds(store_opener):
    svc = _svc(store_opener)
    kinds = {k["kind"] for k in svc.palette()}
    assert "market" in kinds
    assert "strategist" in kinds
    market = next(k for k in svc.palette() if k["kind"] == "market")
    assert market["singleton"] is False
    assert "reports" in market["writes"]


async def test_save_cannot_strip_builtin_protection(store_opener):
    """A client saving 'evaluate_initiative' with builtin=False must not
    bypass delete()'s builtin guard (carried-forward C3 review fix)."""
    svc = _svc(store_opener)
    await svc.list()  # seed the builtin default
    defn = await svc.get("evaluate_initiative")
    payload = defn.model_dump(mode="json")
    payload["builtin"] = False

    await svc.save(payload)

    reloaded = await svc.get("evaluate_initiative")
    assert reloaded.builtin is True
    with pytest.raises(ValueError, match="built-in"):
        await svc.delete("evaluate_initiative")


async def test_show_topology_reflects_human_in_the_loop(store_opener):
    """The GUI always builds with human_in_the_loop=True; show()'s topology
    preview must include the approval step it will actually pause at."""
    hitl_svc = WorkflowService.create(
        FakeChatModel({}),
        persist_events=False,
        store_opener=store_opener,
        human_in_the_loop=True,
    )
    await hitl_svc.list()  # seed
    hitl_detail = await hitl_svc.show("evaluate_initiative")
    assert hitl_detail is not None
    assert "human_approval" in {n["id"] for n in hitl_detail["topology"]["nodes"]}

    plain_svc = _svc(store_opener)
    plain_detail = await plain_svc.show("evaluate_initiative")
    assert plain_detail is not None
    assert "human_approval" not in {n["id"] for n in plain_detail["topology"]["nodes"]}
