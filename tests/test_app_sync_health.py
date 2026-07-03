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
