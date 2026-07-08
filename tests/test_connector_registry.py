"""Entry-point discovery of installed connectors."""

from importlib.metadata import EntryPoint

from productagents.connectors import registry
from productagents.connectors.base import (
    Connector,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.core.models import CustomerFeedback


class _Dummy(Connector):
    key = "dummy"
    produces = frozenset({CustomerFeedback})

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True)

    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        return SyncResult(connector=self.key)


def test_discover_maps_key_to_class(monkeypatch):
    ep = EntryPoint(
        name="dummy",
        value="tests.test_connector_registry:_Dummy",
        group="productagents.connectors",
    )
    monkeypatch.setattr(registry, "entry_points", lambda group: [ep])

    found = registry.discover()

    assert found == {"dummy": _Dummy}


def test_discover_empty_when_no_entry_points(monkeypatch):
    monkeypatch.setattr(registry, "entry_points", lambda group: [])
    assert registry.discover() == {}


def test_discover_finds_real_github_connector():
    from productagents.connectors.github.connector import GitHubConnector

    found = registry.discover()

    assert found.get("github") is GitHubConnector


def test_discover_finds_real_jira_connector():
    from productagents.connectors.jira.connector import JiraConnector

    found = registry.discover()

    assert found.get("jira") is JiraConnector


def test_discover_finds_real_obsidian_connector():
    from productagents.connectors.obsidian.connector import ObsidianConnector

    found = registry.discover()

    assert found.get("obsidian") is ObsidianConnector


def test_discover_skips_a_broken_entry_point(monkeypatch, caplog):
    from importlib.metadata import EntryPoint

    from productagents.connectors import registry
    from productagents.connectors.base import Connector

    class _Good(Connector):
        key = "good"

    good = EntryPoint(name="good", value="x:_Good", group=registry._GROUP)
    bad = EntryPoint(name="bad", value="x:Missing", group=registry._GROUP)

    def _load(self):
        if self.name == "good":
            return _Good
        raise ImportError("boom")

    monkeypatch.setattr(EntryPoint, "load", _load)
    monkeypatch.setattr(registry, "entry_points", lambda group: [good, bad])

    with caplog.at_level("WARNING", logger="productagents.connectors"):
        found = registry.discover()

    assert set(found) == {"good"}  # the broken one is skipped, not fatal
    assert "bad" in caplog.text
