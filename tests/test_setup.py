"""Tests for the static config-readiness check and helpers."""

import os

from productagents.setup import (
    PROVIDERS,
    ConfigStatus,
    ProviderInfo,
    api_key_var_for,
    check_config,
    provider_for,
    write_env,
)


def test_providers_covers_all_expected_keys():
    expected = {
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "XAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_CN_API_KEY",
        "ZHIPU_API_KEY",
        "ZHIPU_CN_API_KEY",
        "MINIMAX_API_KEY",
        "MINIMAX_CN_API_KEY",
        "OPENROUTER_API_KEY",
        "MISTRAL_API_KEY",
        "MOONSHOT_API_KEY",
        "GROQ_API_KEY",
        "NVIDIA_API_KEY",
    }
    actual = {info.key_var for info in PROVIDERS.values()}
    assert actual == expected


def test_providers_all_have_default_model_with_provider_prefix():
    for pid, info in PROVIDERS.items():
        assert isinstance(info, ProviderInfo)
        assert info.default_model.startswith(f"{pid}:"), (
            f"{pid}: default model '{info.default_model}' must start with '{pid}:'"
        )


def test_providers_cn_variants_present():
    assert "dashscope_cn" in PROVIDERS
    assert "zhipu_cn" in PROVIDERS
    assert "minimax_cn" in PROVIDERS
    assert PROVIDERS["dashscope_cn"].key_var == "DASHSCOPE_CN_API_KEY"


def test_provider_for_parses_prefix():
    assert provider_for("anthropic:claude-sonnet-4-6") == "anthropic"


def test_provider_for_explicit_override_wins():
    assert provider_for("some-model", "openai") == "openai"


def test_provider_for_bare_model_is_unknown():
    assert provider_for("just-a-model") == ""


def test_api_key_var_for_known_provider():
    assert api_key_var_for("anthropic") == "ANTHROPIC_API_KEY"


def test_api_key_var_for_unknown_provider_is_derived():
    assert api_key_var_for("cohere") == "COHERE_API_KEY"


def test_api_key_var_for_empty_provider():
    assert api_key_var_for("") == ""


def test_check_config_ok_when_key_present():
    env = {
        "PRODUCTAGENTS_MODEL": "anthropic:claude-sonnet-4-6",
        "ANTHROPIC_API_KEY": "sk-test",
    }
    status = check_config(env)
    assert isinstance(status, ConfigStatus)
    assert status.ok is True
    assert status.provider == "anthropic"
    assert status.key_var == "ANTHROPIC_API_KEY"
    assert status.key_present is True
    assert status.problems == []


def test_check_config_reports_missing_key():
    env = {"PRODUCTAGENTS_MODEL": "anthropic:claude-sonnet-4-6"}
    status = check_config(env)
    assert status.ok is False
    assert status.key_present is False
    assert any("ANTHROPIC_API_KEY" in p for p in status.problems)


def test_check_config_reports_unknown_provider():
    env = {"PRODUCTAGENTS_MODEL": "mystery-model"}
    status = check_config(env)
    assert status.ok is False
    assert status.provider == ""
    assert any("provider" in p.lower() for p in status.problems)


def test_check_config_defaults_to_anthropic_when_model_unset():
    status = check_config({})
    assert status.provider == "anthropic"
    assert status.key_var == "ANTHROPIC_API_KEY"


def test_check_config_blank_key_is_not_present():
    env = {"PRODUCTAGENTS_MODEL": "anthropic:m", "ANTHROPIC_API_KEY": "   "}
    status = check_config(env)
    assert status.key_present is False
    assert status.ok is False


def test_write_env_creates_file_and_sets_process_env(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env_file = tmp_path / ".env"

    path = write_env(
        {
            "PRODUCTAGENTS_MODEL": "anthropic:claude-sonnet-4-6",
            "ANTHROPIC_API_KEY": "sk-test",
        },
        dotenv_path=env_file,
    )

    assert path == str(env_file)
    assert env_file.exists()
    contents = env_file.read_text()
    assert "PRODUCTAGENTS_MODEL" in contents
    assert "sk-test" in contents
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test"
    assert os.environ["PRODUCTAGENTS_MODEL"] == "anthropic:claude-sonnet-4-6"


def test_write_env_preserves_existing_lines(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_VAR=keep-me\n")

    write_env({"OPENAI_API_KEY": "sk-openai"}, dotenv_path=env_file)

    contents = env_file.read_text()
    assert "EXISTING_VAR=keep-me" in contents
    assert "sk-openai" in contents
