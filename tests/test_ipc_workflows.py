"""Tests for the `workflows.list` / `workflows.show` IPC methods."""

from productagents.app import ipc
from productagents.platform.session import Session
from productagents.platform.workflow import Workflow, WorkflowService
from tests._ipc_helpers import _collect, _FakeSessions, _workflows


async def test_workflows_list_returns_registered_workflows():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 1, "method": "workflows.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 1,
            "result": [
                {
                    "name": "evaluate_initiative",
                    "title": "Evaluate Initiative",
                    "description": "advisory pipeline",
                }
            ],
        }
    ]


def _topology_workflow(topology):
    async def _stream():
        return
        yield  # async generator

    return Workflow(
        name="evaluate_initiative",
        title="Evaluate Initiative",
        description="d",
        start=lambda *a, **k: (
            Session(id="x", workflow="evaluate_initiative"),
            _stream(),
        ),
        topology=topology,
    )


def _show_services(wf):
    return {
        "workflows": WorkflowService([wf]),
        "workspaces": None,
        "active_name": "default",
        "sessions": _FakeSessions(),
    }


async def test_workflows_show_returns_topology():
    topo = {
        "nodes": [{"id": "strategist", "prompts": ["strategist"]}],
        "edges": [
            {"source": "__start__", "target": "strategist", "conditional": False}
        ],
    }
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 60,
            "method": "workflows.show",
            "params": {"name": "evaluate_initiative"},
        },
        _show_services(_topology_workflow(lambda: topo)),
        emit=emit,
    )
    assert sink == [
        {
            "id": 60,
            "result": {
                "name": "evaluate_initiative",
                "title": "Evaluate Initiative",
                "description": "d",
                "topology": topo,
            },
        }
    ]


async def test_workflows_show_without_topology_returns_null():
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 61,
            "method": "workflows.show",
            "params": {"name": "evaluate_initiative"},
        },
        _show_services(_topology_workflow(None)),
        emit=emit,
    )
    assert sink[0]["result"]["topology"] is None


async def test_workflows_show_unknown_name_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 62, "method": "workflows.show", "params": {"name": "nope"}},
        _show_services(_topology_workflow(None)),
        emit=emit,
    )
    assert sink == [{"id": 62, "error": "no such workflow: 'nope'"}]
