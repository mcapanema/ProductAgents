"""Cross-table workspace operations on the canonical store's tables."""

from typing import cast

from sqlalchemy import ColumnElement, update
from sqlmodel.ext.asyncio.session import AsyncSession

from productagents.knowledge.repositories.sqlmodel.tables import (
    CanonicalRecord,
    SyncStateRecord,
)


async def rename_workspace(session: AsyncSession, old: str, new: str) -> None:
    """Move every canonical-store row scoped to ``old`` under ``new``.

    No commit — the caller owns the transaction (see the pa-memory twin).
    """
    # ponytail: sqlmodel type stubs issue; cast to ColumnElement[bool] to work around
    await session.execute(  # ty: ignore[deprecated]
        update(CanonicalRecord)
        .where(cast(ColumnElement[bool], CanonicalRecord.workspace == old))
        .values(workspace=new)
    )
    await session.execute(  # ty: ignore[deprecated]
        update(SyncStateRecord)
        .where(cast(ColumnElement[bool], SyncStateRecord.workspace == old))
        .values(workspace=new)
    )
