"""The connector-facing write boundary.

Connectors push canonical models here and stay ignorant of storage: the sink
owns the session lifecycle and routes each model to the right repository by its
concrete type. Upsert/dedup semantics come from ``CanonicalRepository``.
"""

from collections.abc import Iterable
from typing import Protocol

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from productagents.core.models import CanonicalModel
from productagents.knowledge.repositories.sqlmodel.canonical_repository import (
    CanonicalRepository,
)


class CanonicalSink(Protocol):
    """Where connectors write mapped canonical models."""

    async def write(self, model: CanonicalModel) -> None: ...

    async def write_many(self, models: Iterable[CanonicalModel]) -> None: ...


class DbCanonicalSink:
    """A ``CanonicalSink`` backed by the canonical store."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        workspace: str = "default",
    ) -> None:
        self._sessionmaker = sessionmaker
        self._workspace = workspace

    async def write(self, model: CanonicalModel) -> None:
        async with self._sessionmaker() as session:
            await CanonicalRepository(session, type(model), self._workspace).upsert(
                model
            )

    async def write_many(self, models: Iterable[CanonicalModel]) -> None:
        async with self._sessionmaker() as session:
            for model in models:
                await CanonicalRepository(session, type(model), self._workspace).upsert(
                    model
                )
