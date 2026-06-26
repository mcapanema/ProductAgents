"""Generic repository over the single ``canonical_record`` table.

Parametrized by canonical model type, so one implementation serves every entity.
Dedup/upsert is keyed on ``(connector, vendor_type, vendor_id)`` for synced
records and on the platform id for manual records. A matched vendor record keeps
its original platform id across re-syncs (the id is platform-owned and stable).
"""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from productagents.core.models import CanonicalModel
from productagents.knowledge.repositories.sqlmodel.mapping import from_row, to_row
from productagents.knowledge.repositories.sqlmodel.tables import CanonicalRecord


class CanonicalRepository[T: CanonicalModel]:
    def __init__(self, session: AsyncSession, model_type: type[T]) -> None:
        self._session = session
        self._model_type = model_type

    @property
    def _type_name(self) -> str:
        return self._model_type.__name__

    async def get(self, id: str) -> T | None:
        row = await self._session.get(CanonicalRecord, str(id))
        if row is None or row.model_type != self._type_name:
            return None
        return from_row(row, self._model_type)

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[T]:
        stmt = (
            select(CanonicalRecord)
            .where(CanonicalRecord.model_type == self._type_name)
            .order_by(CanonicalRecord.ingested_at)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.exec(stmt)).all()
        return [from_row(row, self._model_type) for row in rows]

    async def upsert(self, model: T) -> T:
        incoming = to_row(model)
        existing = await self._find_existing(incoming)
        if existing is None:
            self._session.add(incoming)
            await self._session.commit()
            return model
        # Preserve the stable platform id of the pre-existing record; refresh the
        # rest of the row from the newer payload.
        stable_id = existing.pk
        existing.model_type = incoming.model_type
        existing.raw_fingerprint = incoming.raw_fingerprint
        existing.updated_at = incoming.updated_at
        existing.payload = {**incoming.payload, "id": stable_id}
        self._session.add(existing)
        await self._session.commit()
        return from_row(existing, self._model_type)

    async def _find_existing(self, incoming: CanonicalRecord) -> CanonicalRecord | None:
        if incoming.vendor_id is not None:
            stmt = select(CanonicalRecord).where(
                CanonicalRecord.connector == incoming.connector,
                CanonicalRecord.vendor_type == incoming.vendor_type,
                CanonicalRecord.vendor_id == incoming.vendor_id,
            )
            return (await self._session.exec(stmt)).first()
        return await self._session.get(CanonicalRecord, incoming.pk)
