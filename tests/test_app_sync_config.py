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
    from productagents.platform.connectors import load_raw_config

    assert load_raw_config(str(tmp_path / "nope.yaml")) == {}


def test_load_raw_config_reads_connectors_block(tmp_path):
    from productagents.platform.connectors import load_raw_config

    path = tmp_path / "connectors.yaml"
    path.write_text(
        "connectors:\n  github:\n    enabled: true\n    owner: acme\n    repo: w\n"
    )
    raw = load_raw_config(str(path))
    assert raw == {"github": {"enabled": True, "owner": "acme", "repo": "w"}}


def test_plan_resolves_secret_from_env():
    from productagents.platform.connectors import plan_connectors

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
    from productagents.platform.connectors import plan_connectors

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
    from productagents.platform.connectors import plan_connectors

    raw = {"github": {"enabled": False, "owner": "acme", "repo": "w"}}
    plan = plan_connectors(raw, _REGISTRY, {})
    assert plan.configs == {}
    assert plan.problems == []


def test_plan_reports_unknown_connector():
    from productagents.platform.connectors import plan_connectors

    raw = {"jira": {"enabled": True}}
    plan = plan_connectors(raw, _REGISTRY, {})
    assert plan.configs == {}
    assert any("jira" in p for p in plan.problems)


def test_plan_reports_invalid_config():
    from productagents.platform.connectors import plan_connectors

    raw = {"github": {"enabled": True}}  # missing required owner/repo
    plan = plan_connectors(raw, _REGISTRY, {})
    assert "github" not in plan.configs
    assert any("github" in p for p in plan.problems)


def test_plan_connectors_non_mapping_block_degrades():
    from productagents.platform.connectors import plan_connectors

    raw = cast(dict[str, dict], {"github": "not-a-dict"})  # intentional type-violation
    plan = plan_connectors(raw, _REGISTRY, {})
    assert any("github" in p for p in plan.problems)
    assert "github" not in plan.configs


def test_plan_validates_jira_block_with_no_app_change():
    from productagents.connectors.jira.connector import JiraConfig, JiraConnector
    from productagents.platform.connectors import plan_connectors

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
    from productagents.connectors.jira.connector import JiraConnector
    from productagents.platform.connectors import plan_connectors

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


async def test_load_db_config_imports_yaml_once(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from productagents.memory.store import create_all as memory_create_all
    from productagents.memory.workspace_state import ConnectorConfigStore
    from productagents.platform.connectors import load_db_config

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await memory_create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    yaml_path = tmp_path / "connectors.yaml"
    yaml_path.write_text(
        "connectors:\n  github:\n"
        "    owner: acme\n    repo: widgets\n    token_env: GH_TOKEN\n"
    )
    blocks = await load_db_config(maker, config_path=str(yaml_path))
    assert blocks["github"]["owner"] == "acme"
    assert not yaml_path.exists()
    assert (tmp_path / "connectors.yaml.imported").exists()

    # Second read comes from the DB; a re-created YAML is ignored.
    yaml_path.write_text("connectors:\n  github:\n    owner: OTHER\n    repo: r\n")
    blocks = await load_db_config(maker, config_path=str(yaml_path))
    assert blocks["github"]["owner"] == "acme"
    assert yaml_path.exists()  # not re-imported, not renamed

    async with maker() as session:
        assert "github" in await ConnectorConfigStore(session).all()


async def test_load_db_config_malformed_yaml_degrades(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from productagents.memory.store import create_all as memory_create_all
    from productagents.platform.connectors import load_db_config

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await memory_create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    yaml_path = tmp_path / "connectors.yaml"
    yaml_path.write_text("connectors: [unclosed\n")  # deliberate YAML syntax error

    blocks = await load_db_config(maker, config_path=str(yaml_path))
    assert blocks == {}
    assert not yaml_path.exists()
    assert (tmp_path / "connectors.yaml.invalid").exists()

    # Second call: bad file moved aside, so it succeeds cleanly.
    assert await load_db_config(maker, config_path=str(yaml_path)) == {}


async def test_load_db_config_sanitizes_secret_shaped_legacy_value(tmp_path, caplog):
    import logging

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from productagents.memory.store import create_all as memory_create_all
    from productagents.memory.workspace_state import ConnectorConfigStore
    from productagents.platform.connectors import load_db_config

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await memory_create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    yaml_path = tmp_path / "connectors.yaml"
    yaml_path.write_text(
        "connectors:\n"
        "  github:\n"
        "    owner: acme\n"
        "    repo: w\n"
        "    token: ghp_rawsecret\n"
    )
    env_path = tmp_path / ".env"

    caplog.set_level(logging.WARNING)
    blocks = await load_db_config(
        maker, config_path=str(yaml_path), env_path=str(env_path)
    )

    # The diversion is logged so it's visible to a human, not silent.
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("github" in m and "token" in m and "GITHUB_TOKEN" in m for m in warnings)

    # The raw secret never reached the DB — it was replaced by a *_env reference.
    assert "token" not in blocks["github"]
    assert blocks["github"]["token_env"] == "GITHUB_TOKEN"
    assert blocks["github"]["owner"] == "acme"

    async with maker() as session:
        stored = await ConnectorConfigStore(session).all()
    assert "token" not in stored["github"]

    # The raw value landed in .env instead.
    from dotenv import dotenv_values

    assert env_path.exists()
    assert dotenv_values(env_path)["GITHUB_TOKEN"] == "ghp_rawsecret"


async def test_connector_plan_reads_db(tmp_path, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from productagents.connectors.github.connector import GitHubConnector
    from productagents.memory.store import create_all as memory_create_all
    from productagents.memory.workspace_state import ConnectorConfigStore
    from productagents.platform.connectors import connector_plan

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await memory_create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await ConnectorConfigStore(session).set(
            "github", {"owner": "acme", "repo": "widgets", "token_env": "GH_TOKEN"}
        )
    monkeypatch.setenv("PRODUCTAGENTS_CONNECTORS_FILE", str(tmp_path / "none.yaml"))
    plan = await connector_plan(
        registry={"github": GitHubConnector},
        env={"GH_TOKEN": "t"},
        engine=engine,
    )
    assert "github" in plan.configs
    assert plan.problems == []


async def test_load_db_config_handles_race_on_file_rename(tmp_path):
    """N20: load_db_config suppresses FileNotFoundError on race condition."""
    from unittest.mock import patch

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from productagents.memory.store import create_all as memory_create_all
    from productagents.platform.connectors import load_db_config

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    await memory_create_all(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    yaml_path = tmp_path / "connectors.yaml"
    yaml_path.write_text("connectors:\n  github:\n    owner: acme\n    repo: widgets\n")

    # Patch os.replace to raise FileNotFoundError on `.imported` rename (race)
    original_replace = __import__("os").replace

    def mock_replace(src, dst):
        # Raise FileNotFoundError if trying to rename to .imported (simulating race)
        if dst.endswith(".imported"):
            raise FileNotFoundError(f"File not found: {src}")
        return original_replace(src, dst)

    with patch(
        "productagents.platform.connectors.os.replace", side_effect=mock_replace
    ):
        result = await load_db_config(
            sessionmaker=maker,
            workspace="default",
            config_path=str(yaml_path),
        )
    # Should return the loaded config despite the race condition
    assert "github" in result
    assert result["github"]["owner"] == "acme"
