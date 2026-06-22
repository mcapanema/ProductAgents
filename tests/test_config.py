"""Tests for the dotenv-backed configuration loader."""

import os

from productagents.config import env_float, env_int, load_env


def test_load_env_populates_missing_var_from_file(tmp_path, monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_TEST_VAR", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("PRODUCTAGENTS_TEST_VAR=from_file\n")

    loaded = load_env(env_file)

    assert loaded is True
    assert os.environ["PRODUCTAGENTS_TEST_VAR"] == "from_file"


def test_load_env_does_not_override_existing_var(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_TEST_VAR", "from_shell")
    env_file = tmp_path / ".env"
    env_file.write_text("PRODUCTAGENTS_TEST_VAR=from_file\n")

    load_env(env_file)

    assert os.environ["PRODUCTAGENTS_TEST_VAR"] == "from_shell"


def test_load_env_returns_false_when_no_file(tmp_path):
    missing = tmp_path / "nope.env"

    assert load_env(missing) is False


def test_env_int_default_when_unset(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_X", raising=False)
    assert env_int("PRODUCTAGENTS_X", 2) == 2


def test_env_int_parses_value(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_X", "5")
    assert env_int("PRODUCTAGENTS_X", 2) == 5


def test_env_int_non_integer_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_X", "not-a-number")
    assert env_int("PRODUCTAGENTS_X", 2) == 2


def test_env_int_below_minimum_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_X", "0")
    assert env_int("PRODUCTAGENTS_X", 2, minimum=1) == 2
    monkeypatch.setenv("PRODUCTAGENTS_X", "-3")
    assert env_int("PRODUCTAGENTS_X", 1, minimum=0) == 1


def test_env_int_at_minimum_is_kept(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_X", "0")
    assert env_int("PRODUCTAGENTS_X", 1, minimum=0) == 0


def test_env_float_default_when_unset(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_Y", raising=False)
    assert env_float("PRODUCTAGENTS_Y", 0.7) == 0.7


def test_env_float_parses_value(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_Y", "0.85")
    assert env_float("PRODUCTAGENTS_Y", 0.7) == 0.85


def test_env_float_non_float_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_Y", "garbage")
    assert env_float("PRODUCTAGENTS_Y", 0.7) == 0.7


def test_env_float_out_of_range_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_Y", "1.5")
    assert env_float("PRODUCTAGENTS_Y", 0.7, minimum=0.0, maximum=1.0) == 0.7
    monkeypatch.setenv("PRODUCTAGENTS_Y", "-0.1")
    assert env_float("PRODUCTAGENTS_Y", 0.7, minimum=0.0, maximum=1.0) == 0.7
