"""Tests for the JSON-over-stdio IPC adapter."""

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import cast

from productagents.app import ipc
from productagents.platform.events import Event
from productagents.platform.session import Session
from productagents.platform.workflow import Workflow, WorkflowService
from productagents.platform.workspace import Workspace, WorkspaceService


def _collect():
    """Return (emit, sink) where emit is an async fn appending to the sink list."""
    sink: list[dict] = []

    async def emit(message: dict) -> None:
        sink.append(message)

    return emit, sink


class _FakeSessions:
    """Stand-in for SessionService with in-memory rows."""

    def __init__(self, sessions=(), events=None):
        self._sessions = list(sessions)
        self._events = events or {}

    async def list(self):
        return self._sessions

    async def get(self, session_id):
        for s in self._sessions:
            if s.id == session_id:
                return s
        return None

    async def events(self, session_id):
        return self._events.get(session_id, [])


class _FakeWorkspaces:
    def __init__(self, workspaces):
        self._workspaces = list(workspaces)

    def list(self):
        return self._workspaces

    def resolve(self, name=None):
        return self._workspaces[0]


def _workflows():
    start: Callable[..., tuple[Session, AsyncIterator[Event]]] = cast(
        Callable[..., tuple[Session, AsyncIterator[Event]]],
        lambda *a, **k: None,
    )
    return WorkflowService(
        [
            Workflow(
                name="evaluate_initiative",
                title="Evaluate Initiative",
                description="advisory pipeline",
                start=start,
            )
        ]
    )


async def test_workflows_list_returns_registered_workflows():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 1, "method": "workflows.list"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
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


async def test_unknown_method_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 7, "method": "nope.nope"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink == [{"id": 7, "error": "unknown method: 'nope.nope'"}]


async def test_sessions_list_returns_rows():
    emit, sink = _collect()
    s = Session(
        id="abc",
        workflow="evaluate_initiative",
        status="finished",
        created_at=datetime(2026, 6, 28, tzinfo=UTC),
    )
    await ipc.handle(
        {"id": 2, "method": "sessions.list"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions([s]),
        emit=emit,
    )
    assert sink == [
        {
            "id": 2,
            "result": [
                {
                    "id": "abc",
                    "workflow": "evaluate_initiative",
                    "status": "finished",
                    "created_at": "2026-06-28T00:00:00+00:00",
                }
            ],
        }
    ]


async def test_sessions_show_unknown_id_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 3, "method": "sessions.show", "params": {"session_id": "missing"}},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink == [{"id": 3, "error": "no such session: missing"}]


async def test_handler_exception_becomes_error_message():
    # sessions.show with no params dict → KeyError on session_id → error, not crash.
    emit, sink = _collect()
    await ipc.handle(
        {"id": 9, "method": "sessions.show"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[0]["id"] == 9
    assert "error" in sink[0]


async def test_workspaces_list_marks_active(tmp_path):
    ws = Workspace(name="default", root=tmp_path)
    emit, sink = _collect()
    await ipc.handle(
        {"id": 4, "method": "workspaces.list"},
        workflows=_workflows(),
        workspaces=cast(WorkspaceService, _FakeWorkspaces([ws])),
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    result = sink[0]["result"]
    assert result[0]["name"] == "default"
    assert result[0]["active"] is True


async def test_workspaces_show_resolves_workspace(tmp_path):
    ws = Workspace(name="default", root=tmp_path)
    emit, sink = _collect()
    await ipc.handle(
        {"id": 5, "method": "workspaces.show", "params": {}},
        workflows=_workflows(),
        workspaces=cast(WorkspaceService, _FakeWorkspaces([ws])),
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[0]["result"]["name"] == "default"
    assert sink[0]["result"]["active"] is True


from productagents.agents import runner as rn  # noqa: E402
from productagents.core.models import Recommendation  # noqa: E402
from tests.fakes import fake_workflow_service  # noqa: E402


def _rec(text="ship it"):
    return Recommendation(
        recommendation=text,
        confidence=0.8,
        rationale="because",
        expected_outcomes=["outcome"],
        failed=False,
    )


async def test_run_streams_events_then_finished_result():
    async def runner(initiative, evidence, *, approver=None):
        yield rn.ProgressEvent(node="market", message="scanning")
        yield rn.FinishedEvent(
            recommendation=_rec(),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
            prior_lessons=[],
            judgment=None,
        )

    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 5,
            "method": "run",
            "params": {
                "workflow": "evaluate_initiative",
                "title": "New API",
                "evidence": "sample",
            },
        },
        workflows=fake_workflow_service(runner),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )

    event_msgs = [m for m in sink if "event" in m]
    assert event_msgs[0]["event"]["type"] == "SessionStarted"
    assert any(m["event"]["type"] == "NodeProgress" for m in event_msgs)
    terminal = sink[-1]
    assert terminal["id"] == 5
    assert terminal["result"]["status"] == "finished"
    assert isinstance(terminal["result"]["session_id"], str)


async def test_run_reports_failed_status_on_abort():
    async def runner(initiative, evidence, *, approver=None):
        yield rn.RunAbortedEvent(node="market", category="rate_limit", message="429")

    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 6,
            "method": "run",
            "params": {
                "workflow": "evaluate_initiative",
                "title": "X",
                "evidence": "sample",
            },
        },
        workflows=fake_workflow_service(runner),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[-1] == {
        "id": 6,
        "result": {
            "status": "failed",
            "session_id": sink[-1]["result"]["session_id"],
        },
    }


async def test_run_unknown_workflow_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 8, "method": "run", "params": {"workflow": "nope", "title": "X"}},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[0]["id"] == 8
    assert "error" in sink[0]


import json  # noqa: E402


def _line_reader(lines):
    """Async read_line yielding each line then '' (EOF) forever."""
    queue = list(lines)

    async def read_line():
        return queue.pop(0) if queue else ""

    return read_line


async def test_serve_dispatches_each_line_until_eof():
    out: list[str] = []
    read_line = _line_reader(
        [
            json.dumps({"id": 1, "method": "workflows.list"}) + "\n",
            json.dumps({"id": 2, "method": "sessions.list"}) + "\n",
        ]
    )
    await ipc.serve(
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        read_line=read_line,
        write_line=out.append,
    )
    parsed = [json.loads(line) for line in out]
    assert [m["id"] for m in parsed] == [1, 2]
    assert parsed[1]["result"] == []  # no sessions


async def test_serve_reports_invalid_json_and_continues():
    out: list[str] = []
    read_line = _line_reader(
        [
            "not json\n",
            json.dumps({"id": 2, "method": "workflows.list"}) + "\n",
        ]
    )
    await ipc.serve(
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        read_line=read_line,
        write_line=out.append,
    )
    parsed = [json.loads(line) for line in out]
    assert parsed[0]["id"] is None
    assert "invalid json" in parsed[0]["error"]
    assert parsed[1]["id"] == 2  # loop kept going


async def test_serve_skips_blank_lines():
    out: list[str] = []
    read_line = _line_reader(
        ["\n", "   \n", json.dumps({"id": 3, "method": "workflows.list"}) + "\n"]
    )
    await ipc.serve(
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        read_line=read_line,
        write_line=out.append,
    )
    assert [json.loads(line)["id"] for line in out] == [3]
