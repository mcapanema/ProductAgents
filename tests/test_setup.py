"""Tests for the static config-readiness check and helpers."""

from productagents.setup import (
    ConfigStatus,
    api_key_var_for,
    check_config,
    provider_for,
)


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
