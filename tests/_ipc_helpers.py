"""Shared fakes for the IPC adapter tests (test_ipc*.py).

Not a test module (underscore prefix → pytest skips collection). Holds only the
three fakes every area suite's ``services`` dict needs; area-specific fakes live
with their area file.
"""

from collections.abc import AsyncIterator, Callable
from typing import cast

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
