"""Tests for the productagents entry point wiring."""

from productagents.app.tui import app as app_module
from productagents.connectors.base import SyncResult
from productagents.platform.connectors import SyncReport


async def _ok_syncer():
    return SyncReport(
        results=[SyncResult(connector="github", ok=True, written=3)], problems=[]
    )


async def _bad_syncer():
    return SyncReport(
        results=[SyncResult(connector="github", ok=False, error="auth: 401")],
        problems=[],
    )


def test_sync_command_returns_zero_and_prints_on_success(capsys):
    from productagents.app.tui.app import sync_command

    code = sync_command(syncer=_ok_syncer)
    assert code == 0
    assert "github" in capsys.readouterr().out


def test_sync_command_returns_one_when_a_connector_fails(capsys):
    from productagents.app.tui.app import sync_command

    code = sync_command(syncer=_bad_syncer)
    assert code == 1
    assert "github" in capsys.readouterr().out


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
    assert app._workflow_service is None
    assert app._reflector is None
    assert app._rebuild is not None
