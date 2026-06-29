"""SessionService — read past runtime sessions and replay their event timelines.

The read face of the Event Store. Presentation lists sessions and replays a
session's events through this service, reconstructing typed platform Events —
never touching pa-memory or the EventStore directly.

Note: the Event Store is an execution log, not the system of record. If event
persistence crashes mid-run (the write is logged and swallowed), a session's
status row can stay stuck at ``"running"``; the DecisionStore remains
authoritative for whether a decision actually completed.
"""

from __future__ import annotations

from datetime import datetime

from productagents.platform import events as ev
from productagents.platform.serialization import deserialize_event
from productagents.platform.session import Session

_L = list  # ponytail: 'list' method shadows the builtin under ty; alias keeps it honest


def _to_session(row: dict) -> Session:
    return Session(
        id=row["id"],
        workflow=row["workflow"],
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class SessionService:
    def __init__(self, store_opener) -> None:
        # store_opener: Callable[[], AbstractAsyncContextManager[EventStore]]
        self._open = store_opener

    @classmethod
    def create(cls) -> SessionService:
        from productagents.platform.context import open_event_store

        return cls(open_event_store)

    async def list(self) -> _L[Session]:
        async with self._open() as store:
            return [_to_session(r) for r in await store.sessions()]

    async def get(self, session_id: str) -> Session | None:
        async with self._open() as store:
            row = await store.get_session(session_id)
        return _to_session(row) if row is not None else None

    async def events(self, session_id: str) -> _L[ev.Event]:
        async with self._open() as store:
            rows = await store.events(session_id)
        return [deserialize_event(r["event_type"], r["payload"]) for r in rows]
