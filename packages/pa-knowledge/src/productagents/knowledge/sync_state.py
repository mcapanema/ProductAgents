"""Per-connector incremental-sync cursor persistence (the sync_state store).

Cursors are persisted as plain strings so this layer never imports a connector
type — the app converts them to/from ``SyncCursor`` when threading them through
the runtime. The session is injected by the caller (the app boundary), like the
other stores; this module never builds an engine.
"""

from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from productagents.knowledge.repositories.sqlmodel.tables import SyncStateRecord


class SyncStateStore:
    """Read/write the last cursor each connector returned."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def cursors(self) -> dict[str, str | None]:
        """Every connector's last persisted cursor value, keyed by connector key."""
        rows = (await self._session.exec(select(SyncStateRecord))).all()
        return {row.connector_key: row.cursor_value for row in rows}

    async def last_synced(self) -> dict[str, str]:
        """Each connector's last sync time (updated_at, ISO-8601), by connector key."""
        rows = (await self._session.exec(select(SyncStateRecord))).all()
        return {row.connector_key: row.updated_at.isoformat() for row in rows}

    async def save(self, connector_key: str, cursor_value: str | None) -> None:
        """Upsert one connector's cursor (keyed on ``connector_key``)."""
        await self._session.merge(
            SyncStateRecord(
                connector_key=connector_key,
                cursor_value=cursor_value,
                updated_at=datetime.now(UTC),
            )
        )
        await self._session.commit()
