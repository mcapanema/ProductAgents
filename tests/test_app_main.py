"""Tests for the productagents entry point wiring."""

from productagents.app.tui import app as app_module


def test_main_loads_env_before_building_app(monkeypatch):
    calls = []

    def fake_load_env():
        calls.append("load_env")
        return True

    def fake_configure_logging():
        calls.append("configure_logging")
        return None

    class _StubApp:
        def run(self):
            calls.append("run")

    def fake_build_app():
        calls.append("build_app")
        return _StubApp()

    monkeypatch.setattr(app_module, "load_env", fake_load_env)
    monkeypatch.setattr(app_module, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(app_module, "_build_app", fake_build_app)

    app_module.main()

    assert calls == ["load_env", "configure_logging", "build_app", "run"]


def test_build_app_is_resilient_when_model_init_fails(monkeypatch):
    def boom():
        raise RuntimeError("no api key")

    monkeypatch.setattr(app_module, "get_model", boom)

    app = app_module._build_app()

    # Model init failed, but the app still builds so it can route to setup.
    assert app._runner is None
    assert app._reflector is None
    assert app._rebuild is not None
