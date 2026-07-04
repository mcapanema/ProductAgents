"""DecisionService threads a WorkflowDefinition into the graph build + session."""

from contextlib import asynccontextmanager

from productagents.core.models import Initiative, WorkflowDefinition, WorkflowNodeDef
from productagents.platform.decision_service import DecisionService


@asynccontextmanager
async def _fake_context_opener():
    # build_graph_from_definition is monkeypatched below to raise before it ever
    # touches ctx, so a bare None stands in — no real DB/session needed.
    yield None


async def test_start_session_uses_definition_name_as_workflow(monkeypatch):
    captured = {}

    def fake_build(defn, ctx, *, human_in_the_loop=False):
        captured["name"] = defn.name
        raise RuntimeError("stop after build")  # we only assert wiring

    import productagents.platform.decision_service as ds

    monkeypatch.setattr(ds, "build_graph_from_definition", fake_build)

    # A minimal definition; the run will crash inside _run (caught, session=failed).
    defn = WorkflowDefinition(
        name="my_flow",
        title="My Flow",
        nodes=[WorkflowNodeDef(id="market", kind="market")],
    )
    svc = DecisionService(_fake_context_opener)
    session, stream = svc.start_session(
        Initiative(title="t", description="d"), "sample", definition=defn
    )
    assert session.workflow == "my_flow"

    # start_session's _run is fire-and-forget; drain the stream so the run
    # actually executes (and the fake builder actually fires) before asserting.
    async for _event in stream:
        pass

    assert captured["name"] == "my_flow"
