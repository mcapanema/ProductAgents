"""Shared transaction helper for the knowledge repositories.

Mirrors productagents.memory._tx.commit — duplicated rather than imported
because pa-knowledge and pa-memory are sibling layers that must not import
each other (see the repo's layer rules).
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
