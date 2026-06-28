"""Tests for the productagents CLI front door."""

import pytest

from productagents.app import cli as cli_module
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


def test_sync_command_zero_and_prints_on_success(capsys):
    assert cli_module.sync_command(syncer=_ok_syncer) == 0
    assert "github" in capsys.readouterr().out


def test_sync_command_one_when_a_connector_fails(capsys):
    assert cli_module.sync_command(syncer=_bad_syncer) == 1
    assert "github" in capsys.readouterr().out


def _patch_bootstrap(monkeypatch, calls):
    class _Workspace:
        name = "acme"

    class _Workspaces:
        def resolve(self, name=None):
            calls.append(("resolve", name))
            return _Workspace()

        def activate(self, workspace):
            calls.append(("activate", workspace.name))

    monkeypatch.setattr(cli_module, "WorkspaceService", _Workspaces)
    monkeypatch.setattr(cli_module, "load_env", lambda: calls.append(("load_env",)))
    monkeypatch.setattr(
        cli_module, "configure_logging", lambda: calls.append(("configure_logging",))
    )


def test_main_no_subcommand_launches_tui_after_bootstrap(monkeypatch):
    calls = []
    _patch_bootstrap(monkeypatch, calls)
    monkeypatch.setattr(
        cli_module, "launch_tui", lambda name: calls.append(("launch_tui", name))
    )

    cli_module.main([])

    assert calls == [
        ("resolve", None),
        ("activate", "acme"),
        ("load_env",),
        ("configure_logging",),
        ("launch_tui", "acme"),
    ]


def test_main_workspace_flag_threads_into_resolve(monkeypatch):
    calls = []
    _patch_bootstrap(monkeypatch, calls)
    monkeypatch.setattr(cli_module, "launch_tui", lambda name: None)

    cli_module.main(["--workspace", "acme"])

    assert ("resolve", "acme") in calls


def test_main_sync_dispatches_to_sync_command(monkeypatch):
    calls = []
    _patch_bootstrap(monkeypatch, calls)
    monkeypatch.setattr(cli_module, "sync_command", lambda: 0)

    with pytest.raises(SystemExit) as exc_info:
        cli_module.main(["sync"])
    assert exc_info.value.code == 0
