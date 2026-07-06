"""Tests for `productagents connectors list/health` and `sync --connector`."""

from productagents.app import cli
from productagents.connectors.base import ConnectorConfig, HealthStatus
from productagents.platform.connectors import ConnectorPlan, HealthReport, SyncReport


class _FakeConnectors:
    def __init__(self, *, plan=None, last=None, health=None):
        self._plan = plan or ConnectorPlan(configs={}, problems=[])
        self._last = last or {}
        self._health = health or HealthReport(statuses={}, problems=[])
        self.health_called_with = "unset"

    async def plan(self):
        return self._plan

    async def last_synced(self):
        return self._last

    async def health(self, connector=None):
        self.health_called_with = connector
        return self._health


async def test_connectors_list_prints_names_and_last_synced(capsys):
    service = _FakeConnectors(
        plan=ConnectorPlan(configs={"github": ConnectorConfig()}, problems=[]),
        last={"github": "2026-07-01T00:00:00+00:00"},
    )
    assert await cli.connectors_list(service=service) == 0
    out = capsys.readouterr().out
    assert "github" in out
    assert "2026-07-01" in out


async def test_connectors_list_handles_empty(capsys):
    assert await cli.connectors_list(service=_FakeConnectors()) == 0
    assert "no connectors configured" in capsys.readouterr().out.lower()


async def test_connectors_health_ok_returns_zero(capsys):
    report = HealthReport(
        statuses={"github": HealthStatus(ok=True, detail="200 OK")}, problems=[]
    )
    service = _FakeConnectors(health=report)
    assert await cli.connectors_health(None, service=service) == 0
    assert service.health_called_with is None
    out = capsys.readouterr().out
    assert "github" in out
    assert "200 OK" in out


async def test_connectors_health_scopes_to_named_connector(capsys):
    report = HealthReport(
        statuses={"github": HealthStatus(ok=False, detail="401")}, problems=[]
    )
    service = _FakeConnectors(health=report)
    assert await cli.connectors_health("github", service=service) == 1
    assert service.health_called_with == "github"


def test_sync_command_passes_only_through():
    seen = {}

    async def syncer(*, only=None):
        seen["only"] = only
        return SyncReport(results=[], problems=[])

    cli.sync_command(only="github", syncer=syncer)
    assert seen["only"] == "github"


class _FakeConnectorConfig:
    def __init__(self, entries=(), error=None):
        self._entries = list(entries)
        self._error = error
        self.saved = None

    async def config_list(self):
        return self._entries

    async def config_save(self, connector, config, *, secrets=None):
        if self._error is not None:
            raise ValueError(self._error)
        self.saved = (connector, config, secrets)
        return {"connector": connector, "config": config, "problems": []}


_ENTRY = {
    "connector": "github",
    "installed": True,
    "title": "GitHub",
    "description": "",
    "config": {"repo": "org/repo", "enabled": True},
    "schema": {},
    "problems": [],
}


async def test_connectors_config_list_prints_blocks(capsys):
    service = _FakeConnectorConfig(entries=[_ENTRY])
    assert await cli.connectors_config_list(service=service) == 0
    out = capsys.readouterr().out
    assert "github" in out
    assert "repo: org/repo" in out


async def test_connectors_config_save_parses_typed_pairs(capsys):
    service = _FakeConnectorConfig()
    code = await cli.connectors_config_save(
        "github",
        ["repo=org/repo", "enabled=true", "limit=5"],
        ["GITHUB_TOKEN=abc"],
        service=service,
    )
    assert code == 0
    assert service.saved is not None
    connector, config, secrets = service.saved
    assert connector == "github"
    assert config == {"repo": "org/repo", "enabled": True, "limit": 5}
    assert secrets == {"GITHUB_TOKEN": "abc"}
    assert "saved github" in capsys.readouterr().out


async def test_connectors_config_save_rejection_returns_one(capsys):
    service = _FakeConnectorConfig(error="connector 'github': repo is required")
    code = await cli.connectors_config_save("github", [], [], service=service)
    assert code == 1
    assert "repo is required" in capsys.readouterr().out
