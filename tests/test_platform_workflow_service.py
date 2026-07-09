"""WorkflowService — registry over the decision pipeline (V3 Phase 3)."""

from collections.abc import AsyncIterator

import pytest

from productagents.platform import events as ev
from productagents.platform.session import Session
from productagents.platform.workflow import (
    Workflow,
    WorkflowService,
    build_evaluate_initiative,
)
from tests.fakes import FakeChatModel


def _simple_wf(start) -> Workflow:
    return Workflow(name="demo", title="Demo", description="a demo", start=start)


def test_list_returns_registered_workflows():
    svc = WorkflowService([_simple_wf(lambda *a, **k: None)])
    assert [w.name for w in svc.list()] == ["demo"]


def test_get_returns_workflow_by_name_or_none():
    wf = _simple_wf(lambda *a, **k: None)
    svc = WorkflowService([wf])
    assert svc.get("demo") is wf
    assert svc.get("missing") is None


def test_run_delegates_to_workflow_start_passing_inputs_through():
    calls = []

    def start(initiative, evidence_spec, *, approver=None):
        calls.append((initiative, evidence_spec, approver))
        return ("session", "stream")

    svc = WorkflowService([_simple_wf(start)])
    result = svc.run("demo", "INIT", "SPEC", approver="cb")

    assert result == ("session", "stream")
    assert calls == [("INIT", "SPEC", "cb")]


def test_run_unknown_workflow_raises_keyerror():
    svc = WorkflowService([])
    with pytest.raises(KeyError):
        svc.run("nope", "x", "y")


def test_for_model_registers_evaluate_initiative():
    svc = WorkflowService.for_model(FakeChatModel({}), persist_events=False)

    names = [w.name for w in svc.list()]
    assert names == ["evaluate_initiative"]

    wf = svc.get("evaluate_initiative")
    assert wf is not None
    assert wf.title == "Evaluate Initiative"
    # start is wired to a real DecisionService.start_session; calling it would
    # need a DB. We only assert it is callable here — the TUI tests exercise run().
    assert callable(wf.start)


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


def test_evaluate_initiative_topology_tracks_human_in_the_loop():
    wf = build_evaluate_initiative(
        FakeChatModel({}), human_in_the_loop=True, persist_events=False
    )
    assert wf.topology is not None
    assert "human_approval" in [n["id"] for n in wf.topology()["nodes"]]


def test_production_threads_model_and_recorder_into_for_model(monkeypatch):
    import productagents.platform.context as context
    import productagents.platform.llm as llm

    captured = {}
    model = FakeChatModel({})
    recorder = object()
    monkeypatch.setattr(llm, "get_model", lambda: model)
    monkeypatch.setattr(
        context, "make_recorder", lambda *, workspace="default": recorder
    )
    # Capture what production() hands to for_model without building real workflows.
    monkeypatch.setattr(
        WorkflowService,
        "for_model",
        classmethod(
            lambda cls, model, **kw: captured.update({"model": model, **kw}) or "SVC"
        ),
    )

    result = WorkflowService.production(human_in_the_loop=True, workspace="acme")

    assert result == "SVC"
    assert captured["model"] is model
    assert captured["recorder"] is recorder
    assert captured["human_in_the_loop"] is True
    assert captured["workspace"] == "acme"
