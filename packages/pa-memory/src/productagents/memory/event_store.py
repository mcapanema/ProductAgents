"""Append-only execution log: runtime sessions + their events.

Complements ``DecisionStore``: the DecisionStore holds the *decisions* (the
system of record); this holds the *execution* — a replayable, timeline-able log
of every event a session emitted.

Like DecisionStore, the ``AsyncSession`` is injected by the platform boundary —
this module builds no engine and never imports pa-knowledge. It is deliberately
ignorant of the platform's ``Event`` vocabulary (which lives a layer above):
it persists primitive rows. Serializing platform Events into those primitives is
the platform's job, which keeps pa-memory below pa-platform in the import DAG.

ponytail: one commit per event over local SQLite. Batch the writes if a session
ever emits enough events that per-event commits show up in a profile.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from productagents.memory.tables import RuntimeEventRow, RuntimeSessionRow


def _session_dict(row: RuntimeSessionRow) -> dict:
    return {
        "id": row.id,
        "workflow": row.workflow,
        "status": row.status,
        "created_at": row.created_at,
    }


class EventStore:
    """Append-only execution log, scoped to one workspace.

    Sessions are scoped to workspace (every read filters on it, every write stamps it).
    Events are globally keyed by session_id (no workspace filtering on event reads).
    """

    def __init__(self, session: AsyncSession, workspace: str = "default") -> None:
        self._session = session
        self._workspace = workspace

    async def start_session(
        self, session_id: str, workflow: str, status: str, created_at: str
    ) -> None:
        await self._session.merge(
            RuntimeSessionRow(
                id=session_id,
                workspace=self._workspace,
                workflow=workflow,
                status=status,
                created_at=created_at,
            )
        )
        await self._session.commit()

    async def update_status(self, session_id: str, status: str) -> None:
        row = await self._session.get(RuntimeSessionRow, session_id)
        if row is not None:
            row.status = status
            await self._session.commit()

    async def append(
        self, session_id: str, seq: int, event_type: str, ts: str, payload: dict
    ) -> None:
        self._session.add(
            RuntimeEventRow(
                session_id=session_id,
                seq=seq,
                event_type=event_type,
                ts=ts,
                payload=payload,
            )
        )
        await self._session.commit()

    async def sessions(self) -> list[dict]:
        """All sessions, newest first."""
        # ponytail: orders by the ISO `created_at` string. Correct because every
        # value is `datetime.now(UTC).isoformat()` (same +00:00 offset), so
        # lexicographic == chronological. Sort on a real datetime column if
        # mixed-offset timestamps ever get stored.
        rows = (
            (
                await self._session.execute(
                    select(RuntimeSessionRow)
                    .where(RuntimeSessionRow.workspace == self._workspace)
                    .order_by(RuntimeSessionRow.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return [_session_dict(r) for r in rows]

    async def get_session(self, session_id: str) -> dict | None:
        row = await self._session.get(RuntimeSessionRow, session_id)
        return _session_dict(row) if row is not None else None

    async def events(self, session_id: str) -> list[dict]:
        """All events for one session, in emission order (by seq)."""
        rows = (
            (
                await self._session.execute(
                    select(RuntimeEventRow)
                    .where(RuntimeEventRow.session_id == session_id)
                    .order_by(RuntimeEventRow.seq)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "session_id": r.session_id,
                "seq": r.seq,
                "event_type": r.event_type,
                "ts": r.ts,
                "payload": r.payload,
            }
            for r in rows
        ]
