"""Tests for the productagents CLI front door."""

import contextlib

import pytest

from productagents.app import cli as cli_module
from productagents.connectors.base import SyncResult
from productagents.core.models import Initiative, Recommendation
from productagents.platform import events as ev
from productagents.platform.connectors import SyncReport
from productagents.platform.session import Session
from productagents.platform.workspace import WorkspaceService


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


def _rec(text="Ship it", conf=0.8):
    return Recommendation(
        recommendation=text,
        confidence=conf,
        rationale="because",
        expected_outcomes=["growth"],
    )


def test_render_event_session_started_and_recommended():
    started = ev.SessionStarted(session_id="s1", seq=0, workflow="evaluate_initiative")
    rec = ev.Recommended(session_id="s1", seq=1, recommendation=_rec())
    started_line = cli_module.render_event(started)
    assert started_line is not None
    assert "s1" in started_line
    rec_line = cli_module.render_event(rec)
    assert rec_line is not None
    assert "Ship it" in rec_line
    assert "80%" in rec_line


def test_render_event_session_failed_marks_abort():
    failed = ev.SessionFailed(
        session_id="s1", seq=9, node="strategist", category="auth", message="401"
    )
    line = cli_module.render_event(failed)
    assert line is not None
    assert "strategist" in line
    assert "auth" in line


class _StubService:
    """Stands in for a real WorkflowService: yields a fixed platform stream."""

    def __init__(self, events):
        self._events = events

    def run(self, name, initiative, evidence_spec):
        session = Session(id="s1", workflow=name)

        async def _stream():
            for e in self._events:
                yield e

        return session, _stream()


async def test_run_workflow_prints_stream_and_returns_zero(capsys):
    events = [
        ev.SessionStarted(session_id="s1", seq=0, workflow="evaluate_initiative"),
        ev.Recommended(session_id="s1", seq=1, recommendation=_rec()),
        ev.SessionFinished(
            session_id="s1",
            seq=2,
            recommendation=_rec(),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
            prior_lessons=[],
            judgment=None,
        ),
    ]
    code = await cli_module.run_workflow(
        "evaluate_initiative", "New onboarding", "", service=_StubService(events)
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "s1" in out
    assert "Ship it" in out


async def test_run_workflow_returns_one_on_session_failed():
    events = [
        ev.SessionStarted(session_id="s1", seq=0, workflow="evaluate_initiative"),
        ev.SessionFailed(
            session_id="s1", seq=1, node="strategist", category="auth", message="401"
        ),
    ]
    code = await cli_module.run_workflow(
        "evaluate_initiative", "x", "", service=_StubService(events)
    )
    assert code == 1


def test_run_workflow_uses_title_as_initiative(monkeypatch, capsys):
    captured = {}

    class _Capturing(_StubService):
        def run(self, name, initiative, evidence_spec):
            captured["initiative"] = initiative
            captured["spec"] = evidence_spec
            return super().run(name, initiative, evidence_spec)

    import asyncio

    asyncio.run(
        cli_module.run_workflow(
            "evaluate_initiative", "Title here", "scenario-x", service=_Capturing([])
        )
    )
    assert isinstance(captured["initiative"], Initiative)
    assert captured["initiative"].title == "Title here"
    assert captured["spec"] == "scenario-x"


def test_workspace_list_marks_active(tmp_path, capsys):
    (tmp_path / "default").mkdir()
    (tmp_path / "acme").mkdir()
    service = WorkspaceService(home=tmp_path)

    code = cli_module.workspace_list(service=service, active_name="acme")

    out = capsys.readouterr().out
    assert code == 0
    assert "acme" in out
    assert "default" in out
    # the active one is flagged
    active_line = next(line for line in out.splitlines() if "acme" in line)
    assert "*" in active_line


def test_workspace_list_empty_home_prints_nothing_and_returns_zero(tmp_path, capsys):
    service = WorkspaceService(home=tmp_path / "missing")
    code = cli_module.workspace_list(service=service, active_name="default")
    assert code == 0
    assert capsys.readouterr().out.strip() == ""


def test_main_workspace_show_without_name_uses_active(monkeypatch):
    calls = []
    _patch_bootstrap(monkeypatch, calls)
    captured = {}
    monkeypatch.setattr(
        cli_module,
        "workspace_show",
        lambda name, *, service: captured.setdefault("name", name) or 0,
    )
    with contextlib.suppress(SystemExit):
        cli_module.main(["--workspace", "acme", "workspace", "show"])
    assert captured["name"] == "acme"


def test_workspace_show_prints_paths(tmp_path, capsys):
    service = WorkspaceService(home=tmp_path)

    code = cli_module.workspace_show("acme", service=service)

    out = capsys.readouterr().out
    assert code == 0
    assert "acme" in out
    assert "productagents.db" in out  # db_url path surfaced
    assert "connectors.yaml" in out
