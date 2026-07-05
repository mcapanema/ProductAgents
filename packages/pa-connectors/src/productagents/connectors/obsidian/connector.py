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
    for note_path in vault.rglob("*.md"):
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

    async def health_check(self) -> HealthStatus:
        """Check that the vault directory exists and is readable."""
        config = cast(ObsidianConfig, self.config)
        vault = Path(config.vault)
        if not vault.is_dir():
            return HealthStatus(ok=False, detail="Vault path not found")
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        """Extract notes since cursor, map and write them, return the new cursor.

        Cursor value is an ISO8601 datetime string representing the max mtime
        seen so far. Notes are written only if their mtime is after this cursor.
        If no new notes are found, the incoming cursor is returned unchanged.
        On any error, degrade gracefully (don't crash) and report it.
        """
        try:
            config = cast(ObsidianConfig, self.config)
            vault = Path(config.vault)
            cursor_dt = None
            if cursor and cursor.value:
                cursor_dt = datetime.fromisoformat(cursor.value)

            max_mtime = cursor_dt
            notes_to_write: list[CustomerFeedback] = []

            for note_path in iter_notes(vault):
                mtime = datetime.fromtimestamp(note_path.stat().st_mtime, tz=UTC)

                # Skip notes at or before the cursor.
                if cursor_dt is not None and mtime <= cursor_dt:
                    continue

                text = note_path.read_text(encoding="utf-8")
                feedback = note_to_feedback(note_path, vault, text, mtime)
                notes_to_write.append(feedback)

                if max_mtime is None or mtime > max_mtime:
                    max_mtime = mtime

            # Write all collected notes.
            if notes_to_write:
                await self.sink.write_many(notes_to_write)

            # Return the new cursor, or keep the incoming one if no progress.
            new_cursor_value = None
            if max_mtime is not None:
                new_cursor_value = max_mtime.isoformat()

            return SyncResult(
                connector=self.key,
                written=len(notes_to_write),
                cursor=SyncCursor(value=new_cursor_value),
                ok=True,
            )

        except (UnicodeDecodeError, OSError, ValueError) as e:
            err = classify_connector_error(e)
            return SyncResult(
                connector=self.key,
                written=0,
                cursor=cursor,
                ok=False,
                error=str(err),
            )
