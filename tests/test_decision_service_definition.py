"""DecisionService threads a WorkflowDefinition into the graph build + session."""

from productagents.core.models import Initiative, WorkflowDefinition, WorkflowNodeDef
from productagents.platform.decision_service import DecisionService


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
    svc = DecisionService.for_model(None, persist_events=False)
    session, _stream = svc.start_session(
        Initiative(title="t", description="d"), "sample", definition=defn
    )
    assert session.workflow == "my_flow"
