"""The Obsidian connector: health check + incremental sync over a local vault.

Reads .md notes from a vault directory, maps them to ``CustomerFeedback`` via
the pure mapper, and writes them incrementally. A ``mtime``-based cursor tracks
progress; notes are written only if their mtime is after the cursor.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, cast

from productagents.connectors.base import (
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.connectors.connector_errors import classify_connector_error
from productagents.connectors.obsidian.mappers import note_to_feedback
from productagents.core.models import CustomerFeedback


def iter_notes(vault: Path):
    """Yield ``.md`` files from a vault, skipping dot directories."""
    for note_path in sorted(vault.rglob("*.md")):
        # Skip any note under a dot directory.
        if any(part.startswith(".") for part in note_path.relative_to(vault).parts):
            continue
        yield note_path


class ObsidianConfig(ConnectorConfig):
    """Obsidian connector config: the vault root path."""

    vault: str


class ObsidianConnector(Connector):
    """The Obsidian connector: reads a local vault, maps notes to feedback."""

    key: ClassVar[str] = "obsidian"
    produces: ClassVar[frozenset[type[CustomerFeedback]]] = frozenset(
        {CustomerFeedback}
    )
    config_cls: ClassVar[type[ObsidianConfig]] = ObsidianConfig
    title: ClassVar[str] = "Obsidian"
    description: ClassVar[str] = "Read notes from a local Obsidian vault"

    def _vault(self) -> Path:
        """Normalize vault path: expand user (~) and resolve to absolute."""
        config = cast(ObsidianConfig, self.config)
        return Path(config.vault).expanduser().resolve()

    async def health_check(self) -> HealthStatus:
        """Check that the vault directory exists and is readable."""
        vault = self._vault()
        if not vault.is_dir():
            return HealthStatus(ok=False, detail=f"vault directory not found: {vault}")
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        """Extract notes since cursor, map and write them, return the new cursor.

        Cursor value is an ISO8601 datetime string representing the max mtime
        seen so far. Notes are written only if their mtime is after this cursor.
        If no new notes are found, the incoming cursor is returned unchanged.
        On any error, degrade gracefully (don't crash) and report it.
        """
        try:
            vault = self._vault()
            cursor_dt = None
            if cursor and cursor.value:
                cursor_dt = datetime.fromisoformat(cursor.value)

            max_mtime = cursor_dt
            written = 0

            for note_path in iter_notes(vault):
                mtime = datetime.fromtimestamp(note_path.stat().st_mtime, tz=UTC)
                if cursor_dt is not None and mtime <= cursor_dt:
                    continue
                text = note_path.read_text(encoding="utf-8")
                feedback = note_to_feedback(note_path, vault, text, mtime)
                await self.sink.write_many([feedback])  # stream: write per note
                written += 1
                if max_mtime is None or mtime > max_mtime:
                    max_mtime = mtime

            new_cursor_value = max_mtime.isoformat() if max_mtime is not None else None
            return SyncResult(
                connector=self.key,
                written=written,
                cursor=SyncCursor(value=new_cursor_value),
                ok=True,
            )

        except Exception as exc:  # noqa: BLE001 — degrade-don't-crash
            err = classify_connector_error(exc)
            return SyncResult(
                connector=self.key,
                written=0,
                cursor=cursor,
                ok=False,
                error=str(err),
            )
