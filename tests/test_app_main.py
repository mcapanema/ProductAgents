"""Tests for the productagents entry point wiring."""

import pytest

from productagents.tui import app as app_module


def test_main_loads_env_before_building_app(monkeypatch):
    calls = []

    def fake_load_env():
        calls.append("load_env")
        return True

    def fake_build_app():
        calls.append("build_app")
        raise RuntimeError("stop before app.run()")

    monkeypatch.setattr(app_module, "load_env", fake_load_env)
    monkeypatch.setattr(app_module, "_build_app", fake_build_app)

    with pytest.raises(SystemExit):
        app_module.main()

    assert calls == ["load_env", "build_app"]
