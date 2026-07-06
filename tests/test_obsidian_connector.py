"""The Obsidian connector: health check, sync (happy + cursor + degrade)."""

import os
from datetime import UTC, datetime
from pathlib import Path

from productagents.connectors.base import SyncCursor
from productagents.connectors.obsidian.connector import (
    ObsidianConfig,
    ObsidianConnector,
)
from tests.connector_fakes import FakeSink

_T1 = datetime(2026, 1, 10, tzinfo=UTC)
_T2 = datetime(2026, 1, 12, tzinfo=UTC)


def _write_note(vault: Path, relpath: str, text: str, when: datetime) -> Path:
    path = vault / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, (when.timestamp(), when.timestamp()))
    return path


def _connector(vault: Path, sink: FakeSink) -> ObsidianConnector:
    return ObsidianConnector(ObsidianConfig(vault=str(vault)), sink)


async def test_health_check_ok(tmp_path):
    status = await _connector(tmp_path, FakeSink()).health_check()
    assert status.ok is True


async def test_health_check_degrades_on_missing_vault(tmp_path):
    status = await _connector(tmp_path / "nope", FakeSink()).health_check()
    assert status.ok is False
    assert "not found" in status.detail


async def test_sync_writes_notes_and_advances_cursor(tmp_path):
    _write_note(tmp_path, "a.md", "alpha", _T1)
    _write_note(tmp_path, "sub/b.md", "beta", _T2)
    sink = FakeSink()

    result = await _connector(tmp_path, sink).sync(None)

    assert result.ok is True
    assert result.written == 2
    assert result.cursor is not None
    assert result.cursor.value is not None
    assert result.cursor.value == _T2.isoformat()  # max mtime
    assert {fb.source.vendor_id for fb in sink.written} == {"a.md", "sub/b.md"}


async def test_sync_skips_notes_at_or_before_cursor(tmp_path):
    _write_note(tmp_path, "old.md", "old", _T1)
    _write_note(tmp_path, "new.md", "new", _T2)
    sink = FakeSink()

    result = await _connector(tmp_path, sink).sync(SyncCursor(value=_T1.isoformat()))

    assert result.written == 1
    assert sink.written[0].source.vendor_id == "new.md"
    assert result.cursor is not None
    assert result.cursor.value is not None
    assert result.cursor.value == _T2.isoformat()


async def test_sync_keeps_incoming_cursor_when_no_new_notes(tmp_path):
    _write_note(tmp_path, "a.md", "alpha", _T1)

    result = await _connector(tmp_path, FakeSink()).sync(
        SyncCursor(value=_T2.isoformat())
    )

    assert result.written == 0
    assert result.cursor is not None
    assert result.cursor.value is not None
    assert result.cursor.value == _T2.isoformat()


async def test_sync_ignores_dot_directories(tmp_path):
    _write_note(tmp_path, ".obsidian/templates/t.md", "template", _T1)
    _write_note(tmp_path, ".trash/gone.md", "deleted", _T1)
    _write_note(tmp_path, "keep.md", "kept", _T1)
    sink = FakeSink()

    result = await _connector(tmp_path, sink).sync(None)

    assert result.written == 1
    assert sink.written[0].source.vendor_id == "keep.md"


async def test_sync_degrades_on_unreadable_note(tmp_path):
    (tmp_path / "bad.md").write_bytes(b"\xff\xfe\xfa")  # not valid UTF-8

    result = await _connector(tmp_path, FakeSink()).sync(None)

    assert result.ok is False
    assert result.error
    assert result.connector == "obsidian"
