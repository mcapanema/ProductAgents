"""Config readiness + write, now a platform service."""

import os

from productagents.platform.configuration import (
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


def test_service_set_writes_active_workspace_env(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    svc = ConfigurationService(workspaces=WorkspaceService(tmp_path), active_name="ws")
    status = svc.set("openai:gpt-4o", api_key="sk-test")
    env_file = tmp_path / "ws" / ".env"
    assert env_file.exists()
    contents = env_file.read_text()
    assert "PRODUCTAGENTS_MODEL" in contents
    assert "sk-test" in contents
    assert "PRODUCTAGENTS_MODEL_PROVIDER" not in contents  # derivable from prefix
    assert os.environ["OPENAI_API_KEY"] == "sk-test"
    assert isinstance(status, ConfigStatus)


def test_service_set_skips_blank_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    svc = ConfigurationService(workspaces=WorkspaceService(tmp_path), active_name="ws")
    svc.set("openai:gpt-4o", api_key="")
    assert "OPENAI_API_KEY" not in (tmp_path / "ws" / ".env").read_text()


def test_service_providers_returns_catalog():
    svc = ConfigurationService(workspaces=WorkspaceService(), active_name="default")
    assert svc.providers() is PROVIDERS


def test_current_settings_defaults(monkeypatch):
    from productagents.platform.configuration import current_settings

    for var in (
        "PRODUCTAGENTS_DEBATE_ROUNDS",
        "PRODUCTAGENTS_JUDGE_THRESHOLD",
        "PRODUCTAGENTS_JUDGE_MAX_RETRIES",
        "PRODUCTAGENTS_MAX_RETRIES",
        "PRODUCTAGENTS_LOG_LEVEL",
        "PRODUCTAGENTS_GITHUB_REPO",
        "PRODUCTAGENTS_GITHUB_TOKEN",
    ):
        monkeypatch.delenv(var, raising=False)
    settings = current_settings()
    assert settings == {
        "debate_rounds": 2,
        "judge_threshold": 0.7,
        "judge_max_retries": 1,
        "max_retries": 6,
        "log_level": "INFO",
        "github_repo": "",
        "github_token_present": False,
    }


def test_current_settings_reads_env(monkeypatch):
    from productagents.platform.configuration import current_settings

    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "3")
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_THRESHOLD", "0.9")
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "0")
    monkeypatch.setenv("PRODUCTAGENTS_MAX_RETRIES", "2")
    monkeypatch.setenv("PRODUCTAGENTS_LOG_LEVEL", "debug")
    monkeypatch.setenv("PRODUCTAGENTS_GITHUB_REPO", "acme/widgets")
    monkeypatch.setenv("PRODUCTAGENTS_GITHUB_TOKEN", "ghp_secret")
    settings = current_settings()
    assert settings["debate_rounds"] == 3
    assert settings["judge_threshold"] == 0.9
    assert settings["judge_max_retries"] == 0
    assert settings["max_retries"] == 2
    assert settings["log_level"] == "DEBUG"
    assert settings["github_repo"] == "acme/widgets"
    # The token value itself must never appear — only presence.
    assert settings["github_token_present"] is True
    assert "ghp_secret" not in str(settings)


def test_service_settings_delegates(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_DEBATE_ROUNDS", raising=False)
    svc = ConfigurationService()
    assert svc.settings()["debate_rounds"] == 2


def test_service_set_writes_whitelisted_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    svc = ConfigurationService(workspaces=WorkspaceService(tmp_path), active_name="ws")
    svc.set(
        "anthropic:claude-sonnet-4-6",
        settings={
            "debate_rounds": 3,
            "judge_threshold": 0.8,
            "judge_max_retries": 2,
            "max_retries": 4,
            "log_level": "DEBUG",
            "github_repo": "acme/widgets",
            "github_token": "ghp_new",
            "evil_key": "ignored",  # not whitelisted → never written
        },
    )
    env_text = (tmp_path / "ws" / ".env").read_text()
    assert "PRODUCTAGENTS_DEBATE_ROUNDS='3'" in env_text
    assert "PRODUCTAGENTS_JUDGE_THRESHOLD='0.8'" in env_text
    assert "PRODUCTAGENTS_JUDGE_MAX_RETRIES='2'" in env_text
    assert "PRODUCTAGENTS_MAX_RETRIES='4'" in env_text
    assert "PRODUCTAGENTS_LOG_LEVEL='DEBUG'" in env_text
    assert "PRODUCTAGENTS_GITHUB_REPO='acme/widgets'" in env_text
    assert "PRODUCTAGENTS_GITHUB_TOKEN='ghp_new'" in env_text
    assert "evil_key" not in env_text
    assert "EVIL_KEY" not in env_text


def test_service_set_blank_token_keeps_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_GITHUB_TOKEN", "ghp_old")
    svc = ConfigurationService(workspaces=WorkspaceService(tmp_path), active_name="ws")
    svc.set("anthropic:m", settings={"github_token": "", "github_repo": ""})
    env_text = (tmp_path / "ws" / ".env").read_text()
    # Blank secret is skipped; blank repo is written (disables the connector).
    assert "PRODUCTAGENTS_GITHUB_TOKEN" not in env_text
    assert "PRODUCTAGENTS_GITHUB_REPO=''" in env_text
    assert os.environ["PRODUCTAGENTS_GITHUB_TOKEN"] == "ghp_old"
