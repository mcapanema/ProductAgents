from collections.abc import AsyncIterator

from productagents.platform import events as ev
from productagents.platform.session import Session
from productagents.platform.workflow import (
    Workflow,
    WorkflowService,
    build_evaluate_initiative,
)
from tests.fakes import FakeChatModel


async def _no_stream() -> AsyncIterator[ev.Event]:
    return
    yield  # make it an async generator


def _wf(name, cancel):
    return Workflow(
        name=name,
        title=name,
        description="t",
        start=lambda *a, **k: (Session(id="x", workflow=name), _no_stream()),
        cancel=cancel,
    )


def test_cancel_routes_to_owning_workflow():
    seen = []
    svc = WorkflowService(
        [
            _wf("a", lambda sid: (seen.append(("a", sid)), False)[1]),
            _wf("b", lambda sid: (seen.append(("b", sid)), True)[1]),
        ]
    )
    assert svc.cancel("sess-1") is True  # any True wins
    assert ("a", "sess-1") in seen
    assert ("b", "sess-1") in seen


def test_cancel_false_when_no_workflow_owns_it():
    svc = WorkflowService([_wf("a", lambda sid: False)])
    assert svc.cancel("nope") is False


def test_workflow_topology_defaults_to_none():
    assert _wf("a", None).topology is None


def test_evaluate_initiative_exposes_graph_topology():
    wf = build_evaluate_initiative(FakeChatModel({}), persist_events=False)
    assert wf.topology is not None
    topo = wf.topology()
    ids = [n["id"] for n in topo["nodes"]]
    assert "strategist" in ids
    assert "human_approval" not in ids  # HITL off by default
    assert {"source": "risk", "target": "governance", "conditional": False} in topo[
        "edges"
    ]


def test_evaluate_initiative_topology_ignores_human_in_the_loop():
    """Topology is now derived from the definition, not the graph build flags."""
    wf_default = build_evaluate_initiative(FakeChatModel({}), persist_events=False)
    wf_with_hitl = build_evaluate_initiative(
        FakeChatModel({}), human_in_the_loop=True, persist_events=False
    )
    assert wf_default.topology is not None
    assert wf_with_hitl.topology is not None
    # Both have the same topology now (definition-driven, not build-time driven)
    assert wf_default.topology() == wf_with_hitl.topology()
