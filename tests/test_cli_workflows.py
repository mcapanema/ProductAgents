"""Tests for `productagents workflows list/show`."""

from productagents.app import cli
from productagents.platform.workflow import Workflow, WorkflowService


def _start(*a, **k):
    return ("", None)


def _workflow(topology=None):
    return Workflow(
        name="evaluate_initiative",
        title="Evaluate Initiative",
        description="Weighs an initiative through five analysts.",
        # ponytail: named fn, not a lambda — ty checks a def's inferred
        # Callable return type more loosely than a lambda's (see
        # test_workflow_registry.py's _dummy_builder for the same pattern).
        start=_start,
        topology=topology,
    )


def test_workflows_list_prints_name_and_title(capsys):
    service = WorkflowService([_workflow()])
    assert cli.workflows_list(service=service) == 0
    out = capsys.readouterr().out
    assert "evaluate_initiative" in out
    assert "Evaluate Initiative" in out


def test_workflows_show_prints_metadata_and_topology(capsys):
    topo = {
        "nodes": [{"id": "debate", "prompts": []}, {"id": "strategist", "prompts": []}],
        "edges": [{"source": "debate", "target": "strategist", "conditional": False}],
    }
    service = WorkflowService([_workflow(topology=lambda: topo)])
    assert cli.workflows_show("evaluate_initiative", service=service) == 0
    out = capsys.readouterr().out
    assert "Evaluate Initiative" in out
    assert "debate ---> strategist" in out


def test_workflows_show_without_topology_still_prints(capsys):
    service = WorkflowService([_workflow()])
    assert cli.workflows_show("evaluate_initiative", service=service) == 0
    assert "Evaluate Initiative" in capsys.readouterr().out


def test_workflows_show_unknown_returns_one(capsys):
    service = WorkflowService([])
    assert cli.workflows_show("nope", service=service) == 1
    assert "no such workflow" in capsys.readouterr().out
