"""WorkflowService — registry over the decision pipeline (V3 Phase 3)."""

import pytest

from productagents.platform.workflow import Workflow, WorkflowService
from tests.fakes import FakeChatModel


def _wf(start) -> Workflow:
    return Workflow(name="demo", title="Demo", description="a demo", start=start)


def test_list_returns_registered_workflows():
    svc = WorkflowService([_wf(lambda *a, **k: None)])
    assert [w.name for w in svc.list()] == ["demo"]


def test_get_returns_workflow_by_name_or_none():
    wf = _wf(lambda *a, **k: None)
    svc = WorkflowService([wf])
    assert svc.get("demo") is wf
    assert svc.get("missing") is None


def test_run_delegates_to_workflow_start_passing_inputs_through():
    calls = []

    def start(initiative, evidence_spec, *, approver=None):
        calls.append((initiative, evidence_spec, approver))
        return ("session", "stream")

    svc = WorkflowService([_wf(start)])
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
