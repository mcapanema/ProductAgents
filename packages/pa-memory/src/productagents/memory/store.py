"""The pa-memory storage face: persist and read full decision/outcome records.

The ``AsyncSession`` is injected by the caller (the app boundary), so this
subsystem never constructs an engine and never imports the canonical store —
keeping the ``knowledge | memory`` sibling-layer boundary intact.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from productagents.core.models import DecisionRecord, OutcomeRecord
from productagents.memory.tables import Base, DecisionRow, OutcomeRow


class DecisionStore:
    """Append/upsert decisions and outcomes; read them back for retrieval.

    Scoped to one workspace: every read filters on it, every write stamps it.
    """

    def __init__(self, session: AsyncSession, workspace: str = "default") -> None:
        self._session = session
        self._workspace = workspace

    async def record(self, decision: DecisionRecord, embedding: list[float]) -> None:
        await self._session.merge(
            DecisionRow(
                decision_id=decision.decision_id,
                workspace=self._workspace,
                initiative_title=decision.initiative.title,
                payload=decision.model_dump(mode="json"),
                embedding=embedding,
                created_at=decision.timestamp,
            )
        )
        await self._session.commit()

    async def record_outcome(self, outcome: OutcomeRecord) -> None:
        self._session.add(
            OutcomeRow(
                decision_id=outcome.decision_id,
                workspace=self._workspace,
                payload=outcome.model_dump(mode="json"),
                reflected_at=outcome.reflected_at,
            )
        )
        await self._session.commit()

    async def decisions(self) -> list[DecisionRecord]:
        """All decisions, oldest first (dedup's 'keep most recent' relies on this)."""
        rows = (
            (
                await self._session.execute(
                    select(DecisionRow)
                    .where(DecisionRow.workspace == self._workspace)
                    .order_by(DecisionRow.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [DecisionRecord.model_validate(row.payload) for row in rows]

    async def outcomes(self) -> list[OutcomeRecord]:
        rows = (
            (
                await self._session.execute(
                    select(OutcomeRow).where(OutcomeRow.workspace == self._workspace)
                )
            )
            .scalars()
            .all()
        )
        return [OutcomeRecord.model_validate(row.payload) for row in rows]

    async def embeddings(self) -> dict[str, list[float]]:
        rows = (
            await self._session.execute(
                select(DecisionRow.decision_id, DecisionRow.embedding).where(
                    DecisionRow.workspace == self._workspace
                )
            )
        ).all()
        return {row.decision_id: row.embedding for row in rows}


async def create_all(engine: AsyncEngine) -> None:
    """Create pa-memory's tables (test convenience; production uses Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
