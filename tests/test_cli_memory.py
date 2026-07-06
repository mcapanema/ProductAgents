"""Tests for `productagents memory lessons`."""

from productagents.app import cli
from productagents.platform.memory_service import Lesson


class _FakeMemory:
    def __init__(self, lessons=()):
        self._lessons = list(lessons)

    async def lessons(self, *, limit=50):
        return self._lessons


async def test_memory_lessons_prints_corpus(capsys):
    lessons = [
        Lesson(
            decision_id="dec-1",
            title="Add SSO",
            text="validate demand earlier",
            validated=True,
            prediction_accuracy=0.4,
        ),
        Lesson(
            decision_id="dec-2",
            title="Dark mode",
            text='Decided "Build it" (80% confidence): users asked',
            validated=False,
            prediction_accuracy=None,
        ),
    ]
    assert await cli.memory_lessons(service=_FakeMemory(lessons)) == 0
    out = capsys.readouterr().out
    assert "dec-1" in out
    assert "validate demand earlier" in out
    assert "40%" in out
    assert "dec-2" in out


async def test_memory_lessons_handles_empty(capsys):
    assert await cli.memory_lessons(service=_FakeMemory()) == 0
    assert "no lessons" in capsys.readouterr().out.lower()
