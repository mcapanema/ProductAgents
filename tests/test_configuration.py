"""Config readiness + write, now a platform service."""

import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.memory.workspace_state import WorkspaceConfigStore
from productagents.platform.configuration import (
    _WORKSPACE_ENV,
    PROVIDERS,
    ConfigStatus,
    ConfigurationService,
    ProviderInfo,
    api_key_var_for,
    check_config,
    provider_for,
    write_env,
)
from productagents.platform.workspace import WorkspaceService


def test_provider_for_parses_prefix():
    assert provider_for("anthropic:claude-sonnet-4-6") == "anthropic"


def test_provider_for_bare_model_is_unknown():
    assert provider_for("just-a-model") == ""


def test_api_key_var_for_known_and_derived():
    assert api_key_var_for("anthropic") == "ANTHROPIC_API_KEY"
    assert api_key_var_for("cohere") == "COHERE_API_KEY"
    assert api_key_var_for("") == ""


def test_check_config_ok_when_key_present():
    status = check_config(
        {"PRODUCTAGENTS_MODEL": "anthropic:m", "ANTHROPIC_API_KEY": "sk"}
    )
    assert isinstance(status, ConfigStatus)
    assert status.ok
    assert status.provider == "anthropic"


def test_check_config_reports_missing_key():
    status = check_config({"PRODUCTAGENTS_MODEL": "anthropic:m"})
    assert status.ok is False
    assert status.key_present is False


def test_providers_have_prefixed_default_models():
    for pid, info in PROVIDERS.items():
        assert isinstance(info, ProviderInfo)
        assert info.default_model.startswith(f"{pid}:")


def test_openrouter_default_is_a_free_tool_calling_model():
    info = PROVIDERS.get("openrouter")
    assert info is not None
    model = info.default_model
    # The default must stay a free tool-calling model (see CLAUDE.md).
    assert ":free" in model or "free" in model.split("/")[-1]


def test_write_env_preserves_existing_lines(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_VAR=keep\n")
    write_env({"NEW_VAR": "value"}, dotenv_path=str(env_file))
    contents = env_file.read_text()
    assert "EXISTING_VAR=keep" in contents
    assert "NEW_VAR=" in contents
    assert "value" in contents


def test_provider_for_explicit_override_wins():
    # The second-arg override path in provider_for must stay covered.
    result = provider_for("some-bare-model", explicit_provider="openai")
    assert result == "openai"


async def test_service_set_skips_blank_api_key(tmp_path, monkeypatch, engine):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    svc = _service(tmp_path, engine)
    await svc.load()
    status = await svc.set("openai:gpt-4o", api_key="")
    env_file = tmp_path / "ws" / ".env"
    assert not env_file.exists() or "OPENAI_API_KEY" not in env_file.read_text()
    assert isinstance(status, ConfigStatus)


def test_service_providers_returns_catalog():
    svc = ConfigurationService(workspaces=WorkspaceService(), active_name="default")
    assert svc.providers() is PROVIDERS


@pytest.fixture
def engine():
    return create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)


@pytest.fixture
def clean_env(monkeypatch):
    for var in _WORKSPACE_ENV.values():
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def _service(tmp_path, engine):
    return ConfigurationService(
        workspaces=WorkspaceService(tmp_path), active_name="ws", engine=engine
    )


async def test_load_materializes_db_into_env(tmp_path, engine, clean_env):
    svc = _service(tmp_path, engine)
    await svc.load()  # bootstraps schema on the injected engine
    async with svc._sessionmaker()() as session:
        await WorkspaceConfigStore(session).set("debate_rounds", "5")
    await svc.load()
    assert os.environ["PRODUCTAGENTS_DEBATE_ROUNDS"] == "5"
    assert svc.settings()["debate_rounds"] == 5
    assert svc.settings_origins()["debate_rounds"] == "db"


async def test_exported_env_wins_over_db(tmp_path, engine, clean_env):
    clean_env.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "9")
    svc = _service(tmp_path, engine)
    await svc.load()
    async with svc._sessionmaker()() as session:
        await WorkspaceConfigStore(session).set("debate_rounds", "5")
    await svc.load()
    assert os.environ["PRODUCTAGENTS_DEBATE_ROUNDS"] == "9"
    assert svc.settings_origins()["debate_rounds"] == "env"


async def test_cli_override_wins_over_everything(tmp_path, engine, clean_env):
    clean_env.setenv("PRODUCTAGENTS_MODEL", "openai:exported")
    svc = _service(tmp_path, engine)
    svc.apply_overrides({"model": "anthropic:cli"})
    await svc.load()
    assert os.environ["PRODUCTAGENTS_MODEL"] == "anthropic:cli"
    assert svc.settings_origins()["model"] == "override"


def test_apply_overrides_rejects_unknown_key(tmp_path, engine):
    with pytest.raises(ValueError, match="unknown setting"):
        _service(tmp_path, engine).apply_overrides({"log_level": "DEBUG"})


async def test_set_writes_db_and_refreshes_seeded_env(tmp_path, engine, clean_env):
    svc = _service(tmp_path, engine)
    await svc.load()
    await svc.set("anthropic:m", settings={"debate_rounds": 3, "evil": "x"})
    async with svc._sessionmaker()() as session:
        stored = await WorkspaceConfigStore(session).all()
    assert stored == {"model": "anthropic:m", "debate_rounds": "3"}
    # Absent from env before -> seeded by the save, next run sees it.
    assert os.environ["PRODUCTAGENTS_DEBATE_ROUNDS"] == "3"
    # Nothing lands in the .env file anymore (secrets only).
    env_file = tmp_path / "ws" / ".env"
    assert not env_file.exists() or "PRODUCTAGENTS_MODEL" not in env_file.read_text()


async def test_set_does_not_clobber_exported_env(tmp_path, engine, clean_env):
    clean_env.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "9")
    svc = _service(tmp_path, engine)
    await svc.load()
    await svc.set("anthropic:m", settings={"debate_rounds": 3})
    assert os.environ["PRODUCTAGENTS_DEBATE_ROUNDS"] == "9"  # export still wins
    async with svc._sessionmaker()() as session:
        assert (await WorkspaceConfigStore(session).all())["debate_rounds"] == "3"


async def test_set_api_key_still_goes_to_env_file(
    tmp_path, engine, clean_env, monkeypatch
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    svc = _service(tmp_path, engine)
    await svc.load()
    await svc.set("anthropic:m", api_key="sk-test")
    env_text = (tmp_path / "ws" / ".env").read_text()
    assert "ANTHROPIC_API_KEY" in env_text
    assert "sk-test" in env_text
    # And the key never enters the DB.
    async with svc._sessionmaker()() as session:
        assert "sk-test" not in str(await WorkspaceConfigStore(session).all())


async def test_load_migrates_env_file_keys_once(tmp_path, engine, clean_env):
    ws_env = tmp_path / "ws" / ".env"
    ws_env.parent.mkdir(parents=True)
    ws_env.write_text(
        "PRODUCTAGENTS_MODEL='openrouter:x'\n"
        "PRODUCTAGENTS_DEBATE_ROUNDS='3'\n"
        "ANTHROPIC_API_KEY='sk-keepme'\n"
        "PRODUCTAGENTS_LOG_LEVEL='DEBUG'\n"
    )
    svc = _service(tmp_path, engine)
    await svc.load()
    async with svc._sessionmaker()() as session:
        stored = await WorkspaceConfigStore(session).all()
    assert stored == {"model": "openrouter:x", "debate_rounds": "3"}
    text = ws_env.read_text()
    # Workspace keys moved out; secrets and runtime keys stay.
    assert "PRODUCTAGENTS_MODEL" not in text
    assert "PRODUCTAGENTS_DEBATE_ROUNDS" not in text
    assert "sk-keepme" in text
    assert "PRODUCTAGENTS_LOG_LEVEL" in text
    # Idempotent: a second load changes nothing.
    await svc.load()
    assert (ws_env.read_text()) == text


async def test_settings_dropped_runtime_and_connector_keys(tmp_path, engine, clean_env):
    svc = _service(tmp_path, engine)
    await svc.load()
    assert set(svc.settings()) == {
        "debate_rounds",
        "judge_threshold",
        "judge_max_retries",
        "max_retries",
    }
