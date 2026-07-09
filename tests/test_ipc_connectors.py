"""Tests for the `connectors.*` IPC methods."""

from productagents.app import ipc
from tests._ipc_helpers import _collect, _FakeSessions, _workflows


class _FakeConnectors:
    """Stand-in for ConnectorService returning canned reports."""

    def __init__(self, plan=None, health=None, sync=None, last_synced=None):
        self._plan = plan
        self._health = health
        self._sync = sync
        self._last_synced = last_synced or {}
        self.health_connector: str | None = "UNSET"
        self.sync_connector: str | None = "UNSET"

    async def plan(self):
        return self._plan

    async def health(self, connector=None):
        self.health_connector = connector
        return self._health

    async def sync(self, connector=None):
        self.sync_connector = connector
        return self._sync

    async def last_synced(self):
        return self._last_synced


async def test_connectors_list_returns_names_only():
    from productagents.connectors import ConnectorConfig
    from productagents.platform.connectors import ConnectorPlan

    plan = ConnectorPlan(
        configs={"github": ConnectorConfig(), "jira": ConnectorConfig()},
        problems=["connector 'slack': unknown (not installed)"],
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 20, "method": "connectors.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": _FakeConnectors(plan=plan),
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 20,
            "result": {
                "connectors": [{"name": "github"}, {"name": "jira"}],
                "problems": ["connector 'slack': unknown (not installed)"],
                "last_synced": {},
            },
        }
    ]


async def test_connectors_list_includes_last_synced_timestamps():
    from productagents.connectors import ConnectorConfig
    from productagents.platform.connectors import ConnectorPlan

    plan = ConnectorPlan(configs={"github": ConnectorConfig()}, problems=[])
    emit, sink = _collect()
    await ipc.handle(
        {"id": 24, "method": "connectors.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": _FakeConnectors(
                plan=plan, last_synced={"github": "2026-06-29T10:00:00+00:00"}
            ),
        },
        emit=emit,
    )
    assert sink[0]["result"]["last_synced"] == {"github": "2026-06-29T10:00:00+00:00"}


async def test_connectors_health_returns_statuses():
    from productagents.connectors import HealthStatus
    from productagents.platform.connectors import HealthReport

    report = HealthReport(
        statuses={"github": HealthStatus(ok=True, detail="reachable")},
        problems=[],
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 21, "method": "connectors.health"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": _FakeConnectors(health=report),
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 21,
            "result": {
                "statuses": {"github": {"ok": True, "detail": "reachable"}},
                "problems": [],
            },
        }
    ]


async def test_connectors_sync_returns_results():
    from productagents.connectors import SyncResult
    from productagents.platform.connectors import SyncReport

    report = SyncReport(
        results=[SyncResult(connector="github", written=7, ok=True, error=None)],
        problems=[],
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 22, "method": "connectors.sync"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": _FakeConnectors(sync=report),
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 22,
            "result": {
                "results": [
                    {"connector": "github", "written": 7, "ok": True, "error": None}
                ],
                "problems": [],
            },
        }
    ]


async def test_connectors_health_forwards_connector_param():
    from productagents.platform.connectors import HealthReport

    fake = _FakeConnectors(health=HealthReport(statuses={}, problems=[]))
    emit, sink = _collect()
    await ipc.handle(
        {"id": 26, "method": "connectors.health", "params": {"connector": "github"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": fake,
        },
        emit=emit,
    )
    assert fake.health_connector == "github"
    assert sink == [{"id": 26, "result": {"statuses": {}, "problems": []}}]


async def test_connectors_sync_forwards_connector_param():
    from productagents.platform.connectors import SyncReport

    fake = _FakeConnectors(sync=SyncReport(results=[], problems=[]))
    emit, sink = _collect()
    await ipc.handle(
        {"id": 27, "method": "connectors.sync", "params": {"connector": "github"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": fake,
        },
        emit=emit,
    )
    assert fake.sync_connector == "github"
    assert sink == [{"id": 27, "result": {"results": [], "problems": []}}]


async def test_connectors_method_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 23, "method": "connectors.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 23
    assert "connectors service not available" in sink[0]["error"]


async def test_connectors_config_list_and_save():
    class _FakeConnectorCfg:
        async def config_list(self):
            return [
                {
                    "connector": "github",
                    "installed": True,
                    "config": {},
                    "schema": {"properties": {}},
                    "problems": [],
                }
            ]

        async def config_save(self, connector, config, secrets=None):
            if config.get("bad"):
                raise ValueError("connector 'github': invalid")
            return {
                "connector": connector,
                "installed": True,
                "config": config,
                "schema": {},
                "problems": [],
            }

    svc = _FakeConnectorCfg()
    emit, sink = _collect()
    await ipc.handle(
        {"id": 63, "method": "connectors.config.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": svc,
        },
        emit=emit,
    )
    assert sink[0]["result"][0]["connector"] == "github"
    await ipc.handle(
        {
            "id": 64,
            "method": "connectors.config.save",
            "params": {"connector": "github", "config": {"owner": "a"}},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": svc,
        },
        emit=emit,
    )
    assert sink[1]["result"]["config"] == {"owner": "a"}
    await ipc.handle(
        {
            "id": 65,
            "method": "connectors.config.save",
            "params": {"connector": "github", "config": {"bad": True}},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "connectors": svc,
        },
        emit=emit,
    )
    assert "invalid" in sink[2]["error"]
