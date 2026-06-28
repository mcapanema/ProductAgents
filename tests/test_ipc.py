"""Tests for the JSON-over-stdio IPC adapter."""

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import cast

from productagents.app import ipc
from productagents.platform.events import Event
from productagents.platform.session import Session
from productagents.platform.workflow import Workflow, WorkflowService


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
