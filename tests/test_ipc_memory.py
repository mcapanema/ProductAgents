"""Tests for the `memory.lessons` IPC method."""

from productagents.app import ipc
from productagents.platform.memory_service import Lesson
from tests._ipc_helpers import _collect, _FakeSessions, _workflows


class _FakeMemory:
    def __init__(self, lessons=()):
        self._lessons = list(lessons)

    async def lessons(self, *, limit=50):
        return self._lessons[:limit]


async def test_memory_lessons_returns_records():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 50, "method": "memory.lessons"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "memory": _FakeMemory(
                [
                    Lesson(
                        decision_id="d1",
                        title="Add SSO",
                        text="took longer",
                        validated=True,
                        prediction_accuracy=0.5,
                    )
                ]
            ),
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 50,
            "result": [
                {
                    "decision_id": "d1",
                    "title": "Add SSO",
                    "text": "took longer",
                    "validated": True,
                    "prediction_accuracy": 0.5,
                }
            ],
        }
    ]


async def test_memory_method_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 51, "method": "memory.lessons"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 51
    assert "memory service not available" in sink[0]["error"]
