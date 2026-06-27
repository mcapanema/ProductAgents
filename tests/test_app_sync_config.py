"""YAML connector config: parse, secret-resolve, typed-validate, fail fast."""

from typing import cast

from productagents.connectors.base import Connector, ConnectorConfig, HealthStatus


class _GHConfig(ConnectorConfig):
    owner: str
    repo: str
    token: str | None = None


class _GHConnector(Connector):
    key = "github"
    produces = frozenset()
    config_cls = _GHConfig

    async def health_check(self) -> HealthStatus:  # pragma: no cover - unused here
        return HealthStatus(ok=True)

    async def sync(self, cursor):  # pragma: no cover - unused here
        ...


_REGISTRY = {"github": _GHConnector}


def test_load_raw_config_missing_file_is_empty(tmp_path):
    from productagents.app.sync import load_raw_config

    assert load_raw_config(str(tmp_path / "nope.yaml")) == {}


def test_load_raw_config_reads_connectors_block(tmp_path):
    from productagents.app.sync import load_raw_config

    path = tmp_path / "connectors.yaml"
    path.write_text(
        "connectors:\n  github:\n    enabled: true\n    owner: acme\n    repo: w\n"
    )
    raw = load_raw_config(str(path))
    assert raw == {"github": {"enabled": True, "owner": "acme", "repo": "w"}}


def test_plan_resolves_secret_from_env():
    from productagents.app.sync import plan_connectors

    raw = {
        "github": {
            "enabled": True,
            "owner": "acme",
            "repo": "w",
            "token_env": "GH_TOKEN",
        }
    }
    plan = plan_connectors(raw, _REGISTRY, {"GH_TOKEN": "secret"})
    assert plan.problems == []
    assert cast(_GHConfig, plan.configs["github"]).token == "secret"


def test_plan_reports_missing_secret():
    from productagents.app.sync import plan_connectors

    raw = {
        "github": {
            "enabled": True,
            "owner": "acme",
            "repo": "w",
            "token_env": "GH_TOKEN",
        }
    }
    plan = plan_connectors(raw, _REGISTRY, {})  # GH_TOKEN unset
    assert any("GH_TOKEN" in p for p in plan.problems)
    assert "github" not in plan.configs  # not built when a secret is missing


def test_plan_skips_disabled():
    from productagents.app.sync import plan_connectors

    raw = {"github": {"enabled": False, "owner": "acme", "repo": "w"}}
    plan = plan_connectors(raw, _REGISTRY, {})
    assert plan.configs == {}
    assert plan.problems == []


def test_plan_reports_unknown_connector():
    from productagents.app.sync import plan_connectors

    raw = {"jira": {"enabled": True}}
    plan = plan_connectors(raw, _REGISTRY, {})
    assert plan.configs == {}
    assert any("jira" in p for p in plan.problems)


def test_plan_reports_invalid_config():
    from productagents.app.sync import plan_connectors

    raw = {"github": {"enabled": True}}  # missing required owner/repo
    plan = plan_connectors(raw, _REGISTRY, {})
    assert "github" not in plan.configs
    assert any("github" in p for p in plan.problems)


def test_static_connector_plan_uses_injected_registry(tmp_path, monkeypatch):
    from productagents.app.sync import static_connector_plan

    path = tmp_path / "c.yaml"
    yaml_content = (
        "connectors:\n  github:\n    enabled: true\n    owner: a\n    repo: b\n"
    )
    path.write_text(yaml_content)
    plan = static_connector_plan(config_path=str(path), registry=_REGISTRY, env={})
    assert set(plan.configs) == {"github"}
    assert plan.problems == []


def test_static_connector_plan_malformed_yaml_degrades(tmp_path):
    from productagents.app.sync import static_connector_plan

    path = tmp_path / "bad.yaml"
    path.write_text("connectors: [unclosed\n")  # deliberate YAML syntax error
    plan = static_connector_plan(config_path=str(path), registry=_REGISTRY, env={})
    assert plan.problems
    assert plan.configs == {}


def test_plan_connectors_non_mapping_block_degrades():
    from productagents.app.sync import plan_connectors

    raw = cast(dict[str, dict], {"github": "not-a-dict"})  # intentional type-violation
    plan = plan_connectors(raw, _REGISTRY, {})
    assert any("github" in p for p in plan.problems)
    assert "github" not in plan.configs


def test_plan_validates_jira_block_with_no_app_change():
    from productagents.app.sync import plan_connectors
    from productagents.connectors.jira.connector import JiraConfig, JiraConnector

    raw = {
        "jira": {
            "enabled": True,
            "base_url": "https://acme.atlassian.net",
            "email": "me@acme.com",
            "token_env": "JIRA_API_TOKEN",
            "project": "PROJ",
        }
    }
    registry = {"jira": JiraConnector}
    env = {"JIRA_API_TOKEN": "secret-token"}

    plan = plan_connectors(raw, registry, env)

    assert plan.problems == []
    config = plan.configs["jira"]
    assert isinstance(config, JiraConfig)
    assert config.base_url == "https://acme.atlassian.net"
    assert config.token == "secret-token"  # resolved from token_env
    assert config.project == "PROJ"


def test_plan_reports_jira_missing_secret_env():
    from productagents.app.sync import plan_connectors
    from productagents.connectors.jira.connector import JiraConnector

    raw = {
        "jira": {
            "enabled": True,
            "base_url": "https://acme.atlassian.net",
            "email": "me@acme.com",
            "token_env": "JIRA_API_TOKEN",
        }
    }
    plan = plan_connectors(raw, {"jira": JiraConnector}, env={})

    assert plan.configs == {}
    assert any("JIRA_API_TOKEN" in p for p in plan.problems)
