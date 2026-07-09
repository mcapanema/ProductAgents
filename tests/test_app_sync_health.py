"""check_connector_health probes connectors without touching the DB."""

from typing import ClassVar

from productagents.connectors.base import (
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.core.models import CustomerFeedback
from productagents.knowledge.repositories.sqlmodel.engine import make_engine


class _HealthyConnector(Connector):
    key: ClassVar[str] = "ok"
    produces = frozenset({CustomerFeedback})
    config_cls = ConnectorConfig

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        return SyncResult(connector=self.key)


class _SickConnector(Connector):
    key: ClassVar[str] = "sick"
    produces = frozenset({CustomerFeedback})
    config_cls = ConnectorConfig

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=False, detail="down")

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        return SyncResult(connector=self.key)


async def test_check_connector_health_probes_each_connector(tmp_path):
    from productagents.platform.connectors import check_connector_health

    path = tmp_path / "connectors.yaml"
    path.write_text(
        "connectors:\n  ok:\n    enabled: true\n  sick:\n    enabled: true\n"
    )

    report = await check_connector_health(
        config_path=str(path),
        registry={"ok": _HealthyConnector, "sick": _SickConnector},
        env={},
        engine=make_engine("sqlite+aiosqlite://"),
    )

    assert report.statuses["ok"].ok is True
    assert report.statuses["sick"].ok is False
    assert report.statuses["sick"].detail == "down"


async def test_describe_health_summarizes_report(tmp_path):
    from productagents.platform.connectors import (
        check_connector_health,
        describe_health,
    )

    path = tmp_path / "connectors.yaml"
    path.write_text("connectors:\n  sick:\n    enabled: true\n")

    report = await check_connector_health(
        config_path=str(path),
        registry={"sick": _SickConnector},
        env={},
        engine=make_engine("sqlite+aiosqlite://"),
    )
    line = describe_health(report)
    assert "sick: ✗ down" in line


async def test_check_connector_health_only_probes_named_connector(tmp_path):
    from productagents.platform.connectors import check_connector_health

    path = tmp_path / "connectors.yaml"
    path.write_text(
        "connectors:\n  ok:\n    enabled: true\n  sick:\n    enabled: true\n"
    )

    report = await check_connector_health(
        config_path=str(path),
        registry={"ok": _HealthyConnector, "sick": _SickConnector},
        env={},
        engine=make_engine("sqlite+aiosqlite://"),
        only="ok",
    )

    assert set(report.statuses) == {"ok"}
    assert report.problems == []


async def test_check_connector_health_only_unknown_connector_reports_problem():
    from productagents.platform.connectors import check_connector_health

    report = await check_connector_health(
        config_path="/nonexistent.yaml",
        registry={"ok": _HealthyConnector},
        env={},
        engine=make_engine("sqlite+aiosqlite://"),
        only="nope",
    )
    assert report.statuses == {}
    assert report.problems == ["connector 'nope': not configured"]


async def test_check_connector_health_no_connectors_is_empty():
    from productagents.platform.connectors import (
        check_connector_health,
        describe_health,
    )

    report = await check_connector_health(
        config_path="/nonexistent.yaml",
        registry={},
        env={},
        engine=make_engine("sqlite+aiosqlite://"),
    )
    assert report.statuses == {}
    assert describe_health(report) == "No connectors configured"


async def test_check_connector_health_only_disabled_connector_reports_problem():
    from productagents.knowledge.repositories.sqlmodel.engine import (
        create_all,
        make_sessionmaker,
    )
    from productagents.memory.store import create_all as memory_create_all
    from productagents.memory.workspace_state import ConnectorConfigStore
    from productagents.platform.connectors import check_connector_health

    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    await memory_create_all(engine)
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        await ConnectorConfigStore(session).set("ok", {"enabled": False})

    report = await check_connector_health(
        registry={"ok": _HealthyConnector},
        env={},
        engine=engine,
        only="ok",
    )

    assert report.statuses == {}
    assert report.problems == ["connector 'ok': no enabled connector matched"]
    await engine.dispose()


class _SecretRequiredConnector(Connector):
    """A connector that requires a secret token."""

    key: ClassVar[str] = "secret_req"
    produces = frozenset({CustomerFeedback})

    class Config(ConnectorConfig):
        token: str

    config_cls = Config

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        return SyncResult(connector=self.key)


async def test_check_connector_health_missing_secret_no_spurious_problem():
    """Regression: enabled connector with missing secret reports only that problem."""
    from productagents.knowledge.repositories.sqlmodel.engine import (
        create_all,
        make_sessionmaker,
    )
    from productagents.memory.store import create_all as memory_create_all
    from productagents.memory.workspace_state import ConnectorConfigStore
    from productagents.platform.connectors import check_connector_health

    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    await memory_create_all(engine)
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        # Connector is enabled but config requires token_env which is not set
        await ConnectorConfigStore(session).set(
            "secret_req", {"enabled": True, "token_env": "MISSING_TOKEN_VAR"}
        )

    report = await check_connector_health(
        registry={"secret_req": _SecretRequiredConnector},
        env={},  # Empty env, so MISSING_TOKEN_VAR is not set
        engine=engine,
        only="secret_req",
    )

    assert report.statuses == {}
    # Should contain only ONE problem about the missing secret, not also the
    # generic "no enabled connector matched"
    assert len(report.problems) == 1
    assert "MISSING_TOKEN_VAR" in report.problems[0]
    assert "no enabled connector matched" not in report.problems[0]
    await engine.dispose()
