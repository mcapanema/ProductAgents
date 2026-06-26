"""The async engine + session factory wire SQLModel to aiosqlite."""

from sqlalchemy import text

from productagents.knowledge.config import database_url
from productagents.knowledge.repositories.sqlmodel.engine import (
    create_all,
    drop_all,
    make_engine,
    make_sessionmaker,
)


def test_database_url_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_DB_URL", raising=False)
    assert database_url() == "sqlite+aiosqlite:///productagents.db"


def test_database_url_honours_env(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DB_URL", "postgresql+asyncpg://x/y")
    assert database_url() == "postgresql+asyncpg://x/y"


async def test_in_memory_engine_persists_across_sessions():
    # StaticPool keeps one connection so an in-memory DB survives session churn.
    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        await session.execute(text("CREATE TABLE probe (x INTEGER)"))  # ty: ignore[deprecated]
        await session.execute(text("INSERT INTO probe VALUES (1)"))  # ty: ignore[deprecated]
        await session.commit()
    async with sessionmaker() as session:
        rows = (await session.execute(text("SELECT x FROM probe"))).all()  # ty: ignore[deprecated]
    assert rows == [(1,)]
    await engine.dispose()


async def test_file_engine_and_drop_all(tmp_path):
    # ponytail: covers the non-memory make_engine branch and drop_all teardown
    url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = make_engine(url)
    await create_all(engine)
    await drop_all(engine)
    await engine.dispose()


def test_public_surface_is_importable():
    from productagents.knowledge import (
        CanonicalRepository,
        CanonicalSink,
        DbCanonicalSink,
        Repository,
        database_url,
        make_engine,
        make_sessionmaker,
    )

    assert all(
        x is not None
        for x in (
            CanonicalRepository,
            CanonicalSink,
            DbCanonicalSink,
            Repository,
            database_url,
            make_engine,
            make_sessionmaker,
        )
    )
