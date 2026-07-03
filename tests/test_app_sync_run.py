"""run_connector_sync wires config → store → sync → cursor persistence."""

from typing import ClassVar

from productagents.connectors.base import (
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.core.models import CustomerFeedback
from productagents.knowledge.repositories.sqlmodel.engine import (
    create_all,
    make_engine,
    make_sessionmaker,
)
from productagents.knowledge.sync_state import SyncStateStore
from productagents.memory.store import create_all as memory_create_all
from productagents.memory.workspace_state import ConnectorConfigStore


class _RecordingConnector(Connector):
    """Writes one feedback row carrying the cursor it received, returns a cursor."""

    key: ClassVar[str] = "rec"
    produces = frozenset({CustomerFeedback})
    config_cls = ConnectorConfig
    seen_cursor: ClassVar[str | None] = "UNSET"

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        type(self).seen_cursor = cursor.value if cursor else None
        await self.sink.write(CustomerFeedback(body="hello"))
        return SyncResult(
            connector=self.key, written=1, cursor=SyncCursor(value="cursor-2")
        )


class _OtherConnector(Connector):
    """A second connector used to prove `only=` scoping."""

    key: ClassVar[str] = "other"
    produces = frozenset({CustomerFeedback})
    config_cls = ConnectorConfig
    synced: ClassVar[bool] = False

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        type(self).synced = True
        return SyncResult(connector=self.key)


async def test_build_connectors_instantiates_from_registry():
    from productagents.platform.connectors import build_connectors

    sink = object()  # not used by construction
    built = build_connectors(
        {"rec": ConnectorConfig()},
        {"rec": _RecordingConnector},
        sink,  # type: ignore
    )
    assert len(built) == 1
    assert isinstance(built[0], _RecordingConnector)
    assert built[0].sink is sink


async def test_run_connector_sync_writes_store_and_persists_cursor():
    from productagents.platform.connectors import run_connector_sync

    _RecordingConnector.seen_cursor = "UNSET"
    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    await memory_create_all(engine)
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        await ConnectorConfigStore(session).set("rec", {"enabled": True})

    report = await run_connector_sync(
        registry={"rec": _RecordingConnector},
        engine=engine,
        env={},
    )

    assert report.problems == []
    assert [r.connector for r in report.results] == ["rec"]
    assert report.results[0].written == 1

    async with sessionmaker() as session:
        assert await SyncStateStore(session).cursors() == {"rec": "cursor-2"}
    await engine.dispose()


async def test_run_connector_sync_threads_stored_cursor_into_connector():
    from productagents.platform.connectors import run_connector_sync

    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    await memory_create_all(engine)
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        await SyncStateStore(session).save("rec", "cursor-1")
        await ConnectorConfigStore(session).set("rec", {"enabled": True})

    _RecordingConnector.seen_cursor = "UNSET"
    await run_connector_sync(
        registry={"rec": _RecordingConnector},
        engine=engine,
        env={},
    )
    assert _RecordingConnector.seen_cursor == "cursor-1"
    await engine.dispose()


async def test_run_connector_sync_no_connectors_returns_problems_only():
    from productagents.platform.connectors import run_connector_sync

    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    report = await run_connector_sync(
        config_path="/nonexistent.yaml",
        registry={"rec": _RecordingConnector},
        engine=engine,
        env={},
    )
    assert report.results == []
    assert report.problems == []
    await engine.dispose()


async def test_run_connector_sync_only_scopes_to_one_connector():
    from productagents.platform.connectors import run_connector_sync

    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    await memory_create_all(engine)
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        await ConnectorConfigStore(session).set("rec", {"enabled": True})
        await ConnectorConfigStore(session).set("other", {"enabled": True})

    _OtherConnector.synced = False
    report = await run_connector_sync(
        registry={"rec": _RecordingConnector, "other": _OtherConnector},
        engine=engine,
        env={},
        only="rec",
    )

    assert [r.connector for r in report.results] == ["rec"]
    assert _OtherConnector.synced is False
    assert report.problems == []
    await engine.dispose()


async def test_run_connector_sync_only_unknown_connector_reports_problem():
    from productagents.platform.connectors import run_connector_sync

    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    await memory_create_all(engine)
    report = await run_connector_sync(
        config_path="/nonexistent.yaml",
        registry={"rec": _RecordingConnector},
        engine=engine,
        env={},
        only="nope",
    )
    assert report.results == []
    assert report.problems == ["connector 'nope': not configured"]
    await engine.dispose()
