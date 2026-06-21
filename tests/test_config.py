"""Tests for the dotenv-backed configuration loader."""

from productagents.config import load_env


def test_load_env_populates_missing_var_from_file(tmp_path, monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_TEST_VAR", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("PRODUCTAGENTS_TEST_VAR=from_file\n")

    loaded = load_env(env_file)

    assert loaded is True
    import os

    assert os.environ["PRODUCTAGENTS_TEST_VAR"] == "from_file"


def test_load_env_does_not_override_existing_var(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_TEST_VAR", "from_shell")
    env_file = tmp_path / ".env"
    env_file.write_text("PRODUCTAGENTS_TEST_VAR=from_file\n")

    load_env(env_file)

    import os

    assert os.environ["PRODUCTAGENTS_TEST_VAR"] == "from_shell"


def test_load_env_returns_false_when_no_file(tmp_path):
    missing = tmp_path / "nope.env"

    assert load_env(missing) is False
