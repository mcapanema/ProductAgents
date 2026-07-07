"""Async engine + session construction for the canonical store.

Production schema is owned by Alembic; ``create_all``/``drop_all`` exist only so
tests can stand up the SQLModel metadata against an ephemeral database.
"""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from productagents.knowledge.config import database_url

# Import for metadata registration side effect: defining the table classes
# attaches them to ``SQLModel.metadata`` so ``create_all`` knows about them.
from productagents.knowledge.repositories.sqlmodel import tables  # noqa: F401

_MEMORY_URLS = {"sqlite+aiosqlite://", "sqlite+aiosqlite:///:memory:"}


def _enable_sqlite_wal(engine: AsyncEngine) -> None:
    """Put the shared file DB in WAL with a busy_timeout so concurrent writers
    (GUI sidecar + cron + CLL) wait for the lock instead of erroring. Fires on
    every new pooled connection."""

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_conn, _record):  # ty: ignore[unused-ignore]
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()


def make_engine(url: str | None = None) -> AsyncEngine:
    """Build an async engine. In-memory SQLite uses a single pooled connection so
    the database survives across sessions within the same engine; a file SQLite
    engine is put in WAL mode with a busy_timeout for multi-process safety."""
    resolved = url or database_url()
    if resolved in _MEMORY_URLS:
        return create_async_engine(
            resolved,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    engine = create_async_engine(resolved)
    if resolved.startswith("sqlite"):
        _enable_sqlite_wal(engine)
    return engine


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
