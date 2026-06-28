"""Tests for the productagents entry point wiring."""

from productagents.app.tui import app as app_module


def test_build_app_is_resilient_when_model_init_fails(monkeypatch):
    def boom():
        raise RuntimeError("no api key")

    monkeypatch.setattr(app_module, "get_model", boom)

    app = app_module._build_app()

    # Model init failed, but the app still builds so it can route to setup.
    assert app._workflow_service is None
    assert app._reflector is None
    assert app._rebuild is not None
