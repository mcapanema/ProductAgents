"""Async engine + session construction for the canonical store.

Production schema is owned by Alembic; ``create_all``/``drop_all`` exist only so
tests can stand up the SQLModel metadata against an ephemeral database.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from productagents.knowledge.config import database_url

# Import for metadata registration side effect: defining the table classes
# attaches them to ``SQLModel.metadata`` so ``create_all`` knows about them.
from productagents.knowledge.repositories.sqlmodel import tables  # noqa: F401

_MEMORY_URLS = {"sqlite+aiosqlite://", "sqlite+aiosqlite:///:memory:"}


def make_engine(url: str | None = None) -> AsyncEngine:
    """Build an async engine. In-memory SQLite uses a single pooled connection so
    the database survives across sessions within the same engine."""
    resolved = url or database_url()
    if resolved in _MEMORY_URLS:
        return create_async_engine(
            resolved,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_async_engine(resolved)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """A session factory yielding SQLModel async sessions (objects stay usable
    after commit, so repositories can return mapped instances)."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_all(engine: AsyncEngine) -> None:
    """Create every registered table (test convenience, not production path)."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_all(engine: AsyncEngine) -> None:
    """Drop every registered table (test teardown convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
