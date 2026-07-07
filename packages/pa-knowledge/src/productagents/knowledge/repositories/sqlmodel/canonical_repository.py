"""Generic repository over the single ``canonical_record`` table.

Parametrized by canonical model type, so one implementation serves every entity.
Dedup/upsert is keyed on ``(connector, vendor_type, vendor_id)`` for synced
records and on the platform id for manual records. A matched vendor record keeps
its original platform id across re-syncs (the id is platform-owned and stable).
"""

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from productagents.core.models import CanonicalModel
from productagents.knowledge._tx import commit as _commit
from productagents.knowledge.repositories.sqlmodel.mapping import from_row, to_row
from productagents.knowledge.repositories.sqlmodel.tables import CanonicalRecord


class CanonicalRepository[T: CanonicalModel]:
    def __init__(
        self, session: AsyncSession, model_type: type[T], workspace: str = "default"
    ) -> None:
        self._session = session
        self._model_type = model_type
        self._workspace = workspace

    @property
    def _type_name(self) -> str:
        return self._model_type.__name__

    async def get(self, id: str) -> T | None:
        row = await self._session.get(CanonicalRecord, str(id))
        if row is None or row.model_type != self._type_name:
            return None
        if row.workspace != self._workspace:
            return None
        return from_row(row, self._model_type)

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[T]:  # ty: ignore[invalid-type-form]  # shadowed-builtin
        stmt = (
            select(CanonicalRecord)
            .where(
                CanonicalRecord.model_type == self._type_name,
                CanonicalRecord.workspace == self._workspace,
            )
            .order_by(CanonicalRecord.ingested_at)  # ty: ignore[invalid-argument-type]  # sqlalchemy-typing
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.exec(stmt)).all()
        return [from_row(row, self._model_type) for row in rows]

    async def upsert(self, model: T) -> T:
        incoming = to_row(model, self._workspace)
        existing = await self._find_existing(incoming)
        if existing is None:
            self._session.add(incoming)
            try:
                await _commit(self._session)
                return model
            except IntegrityError:
                # A concurrent writer inserted the same identity between our
                # find and commit. _commit already rolled back; resolve as an
                # update.
                existing = await self._find_existing(incoming)
                if existing is None:
                    raise  # genuine constraint violation, not the upsert race
        result = self._apply_update(existing, incoming)
        await _commit(self._session)
        return result

    def _apply_update(self, existing: CanonicalRecord, incoming: CanonicalRecord) -> T:
        # Preserve the stable platform id of the pre-existing record; refresh the
        # rest of the row from the newer payload.
        stable_id = existing.pk
        existing.model_type = incoming.model_type
        existing.raw_fingerprint = incoming.raw_fingerprint
        existing.updated_at = incoming.updated_at
        existing.payload = {
            **incoming.payload,
            "id": stable_id,
            "ingested_at": existing.payload["ingested_at"],  # first-seen time is stable
        }
        self._session.add(existing)
        return from_row(existing, self._model_type)

    async def _find_existing(self, incoming: CanonicalRecord) -> CanonicalRecord | None:
        if incoming.vendor_id is not None:
            stmt = select(CanonicalRecord).where(
                CanonicalRecord.workspace == self._workspace,
                CanonicalRecord.connector == incoming.connector,
                CanonicalRecord.vendor_type == incoming.vendor_type,
                CanonicalRecord.vendor_id == incoming.vendor_id,
            )
            return (await self._session.exec(stmt)).first()
        existing = await self._session.get(CanonicalRecord, incoming.pk)
        if existing is None or existing.workspace != self._workspace:
            return None
        return existing
