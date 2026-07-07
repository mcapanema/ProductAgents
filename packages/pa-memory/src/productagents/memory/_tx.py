"""Shared transaction helper for the memory stores.

Both stores commit on a caller-owned per-run session; a raw failed ``commit()``
leaves that session in ``PendingRollbackError`` and poisons every later write in
the run. ``commit`` rolls back on any failure so the session stays usable.
"""

from sqlalchemy.ext.asyncio import AsyncSession


async def commit(session: AsyncSession) -> None:
    """Commit; on any failure roll back (so the shared session stays usable) and
    re-raise for the caller to handle or tolerate."""
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
