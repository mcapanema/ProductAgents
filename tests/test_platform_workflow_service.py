from collections.abc import AsyncIterator

from productagents.platform import events as ev
from productagents.platform.session import Session
from productagents.platform.workflow import Workflow, WorkflowService


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
