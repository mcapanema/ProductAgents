"""Tests for the productagents CLI front door."""

import contextlib
import os
from datetime import UTC, datetime

import pytest

from productagents.app import cli as cli_module
from productagents.connectors.base import SyncResult
from productagents.core.models import Initiative, OutcomeRecord, Recommendation
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


def _decision_record(did="dec-1", title="Add SSO"):
    from productagents.core.models import DecisionRecord, Initiative, Recommendation

    return DecisionRecord(
        decision_id=did,
        initiative=Initiative(title=title, description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.8,
            rationale="r",
            expected_outcomes=["x"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


class _FakeReflection:
    def __init__(self, *, decisions=(), outcome=None, missing=False):
        self._decisions = list(decisions)
        self._outcome = outcome
        self._missing = missing

    async def decisions(self):
        return self._decisions

    async def reflect_on(self, decision_id, note):
        if self._missing:
            raise LookupError(f"no such decision: {decision_id}")
        return self._outcome


async def test_reflect_list_prints_ids_and_titles(capsys):
    svc = _FakeReflection(decisions=[_decision_record("dec-1", "Add SSO")])
    assert await cli_module.reflect_list(service=svc) == 0
    out = capsys.readouterr().out
    assert "dec-1" in out
    assert "Add SSO" in out


async def test_reflect_list_handles_empty(capsys):
    assert await cli_module.reflect_list(service=_FakeReflection()) == 0
    assert "no decisions" in capsys.readouterr().out.lower()


async def test_reflect_record_prints_outcome_and_returns_zero(capsys):
    outcome = OutcomeRecord(
        decision_id="dec-1",
        actual_outcomes=["slow adoption"],
        prediction_accuracy=0.4,
        lessons_learned=["validate demand earlier"],
        reflected_at="2026-06-20T12:00:00+00:00",
    )
    svc = _FakeReflection(outcome=outcome)
    code = await cli_module.reflect_record("dec-1", "shipped", service=svc)
    assert code == 0
    out = capsys.readouterr().out
    assert "40%" in out
    assert "slow adoption" in out
    assert "validate demand earlier" in out


async def test_reflect_record_unknown_decision_returns_one(capsys):
    svc = _FakeReflection(missing=True)
    code = await cli_module.reflect_record("nope", "note", service=svc)
    assert code == 1
    assert "no such decision" in capsys.readouterr().out


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

    class _InertConfig:
        """No-op stand-in: keeps main()'s config wiring off the real
        ~/.productagents home dir for tests that don't care about it."""

        def __init__(self, **_kw):
            pass

        def apply_overrides(self, _overrides):
            pass

        async def load(self):
            pass

    monkeypatch.setattr(cli_module, "WorkspaceService", _Workspaces)
    monkeypatch.setattr(cli_module, "ConfigurationService", _InertConfig)
    monkeypatch.setattr(cli_module, "load_env", lambda: calls.append(("load_env",)))
    monkeypatch.setattr(
        cli_module, "configure_logging", lambda: calls.append(("configure_logging",))
    )


def test_main_no_subcommand_prints_help_after_bootstrap(monkeypatch, capsys):
    calls = []
    _patch_bootstrap(monkeypatch, calls)

    cli_module.main([])

    assert calls == [
        ("resolve", None),
        ("activate", "acme"),
        ("load_env",),
        ("configure_logging",),
    ]
    out = capsys.readouterr().out
    assert "usage: productagents" in out
    assert "reflect" in out  # the new subcommand shows in help


def test_main_workspace_flag_threads_into_resolve(monkeypatch):
    calls = []
    _patch_bootstrap(monkeypatch, calls)

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


class _StubSessionService:
    def __init__(self, sessions, events_by_id):
        self._sessions = sessions
        self._events = events_by_id

    async def list(self):
        return self._sessions

    async def get(self, session_id):
        for s in self._sessions:
            if s.id == session_id:
                return s
        return None

    async def events(self, session_id):
        return self._events.get(session_id, [])


def _session(id_="s1", status="finished"):
    return Session(
        id=id_,
        workflow="evaluate_initiative",
        status=status,
        created_at=datetime(2026, 6, 28, tzinfo=UTC),
    )


async def test_sessions_list_prints_rows(capsys):
    svc = _StubSessionService([_session("s1"), _session("s2", "running")], {})
    code = await cli_module.sessions_list(service=svc)
    out = capsys.readouterr().out
    assert code == 0
    assert "s1" in out
    assert "s2" in out
    assert "running" in out


async def test_sessions_list_empty_returns_zero(capsys):
    code = await cli_module.sessions_list(service=_StubSessionService([], {}))
    assert code == 0
    assert "no sessions" in capsys.readouterr().out.lower()


async def test_sessions_show_replays_events(capsys):
    events = [
        ev.SessionStarted(session_id="s1", seq=0, workflow="evaluate_initiative"),
        ev.Recommended(session_id="s1", seq=1, recommendation=_rec()),
    ]
    svc = _StubSessionService([_session("s1")], {"s1": events})
    code = await cli_module.sessions_show("s1", service=svc)
    out = capsys.readouterr().out
    assert code == 0
    assert "Ship it" in out


async def test_sessions_show_unknown_id_returns_one(capsys):
    svc = _StubSessionService([], {})
    code = await cli_module.sessions_show("missing", service=svc)
    assert code == 1
    assert "missing" in capsys.readouterr().out


def test_main_ipc_dispatches_to_serve_stdio(monkeypatch):
    calls = []
    _patch_bootstrap(monkeypatch, calls)
    monkeypatch.setattr(
        "productagents.app.ipc.serve_stdio",
        lambda name, **_kw: calls.append(("serve_stdio", name)),
    )

    cli_module.main(["ipc"])

    assert ("serve_stdio", "acme") in calls


def test_main_run_unknown_workflow_exits_friendly(monkeypatch):
    calls = []
    _patch_bootstrap(monkeypatch, calls)

    class _Svc:
        def get(self, name):
            return None  # nothing registered → unknown

        def run(self, *a, **k):  # must NOT be reached
            raise AssertionError("run() should not be called for unknown workflow")

    monkeypatch.setattr(cli_module, "_build_run_service", lambda: _Svc())

    with pytest.raises(SystemExit) as exc:
        cli_module.main(["run", "bogus_workflow", "Some title"])
    # friendly: non-zero/str message, not a KeyError traceback
    assert exc.value.code is not None
    assert "bogus_workflow" in str(exc.value.code)


def test_parse_set_overrides_valid():
    from productagents.app.cli import parse_set_overrides

    assert parse_set_overrides(["debate_rounds=3", "model=anthropic:m"]) == {
        "debate_rounds": "3",
        "model": "anthropic:m",
    }


def test_parse_set_overrides_rejects_malformed():
    from productagents.app.cli import parse_set_overrides

    with pytest.raises(SystemExit):
        parse_set_overrides(["debate_rounds"])  # no '='


def test_main_config_load_failure_degrades_and_dispatches(monkeypatch, tmp_path):
    """A corrupt workspace DB must not crash startup — commands still dispatch."""
    import productagents.app.cli as cli

    monkeypatch.setenv("PRODUCTAGENTS_HOME", str(tmp_path))
    calls: list[str] = []

    class _FakeConfig:
        def __init__(self, **_kw):
            pass

        def apply_overrides(self, _overrides):
            calls.append("overrides")

        async def load(self):
            calls.append("load")
            raise RuntimeError("corrupt workspace db")

    monkeypatch.setattr(cli, "ConfigurationService", _FakeConfig)
    # workspace list dispatches fine even though load() raised.
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["workspace", "list"])
    assert exc_info.value.code == 0
    assert calls == ["overrides", "load"]


def test_main_applies_overrides_and_loads(monkeypatch, tmp_path):
    """`--set` lands in the env via the service, and load() runs before dispatch."""
    import productagents.app.cli as cli

    monkeypatch.setenv("PRODUCTAGENTS_HOME", str(tmp_path))
    monkeypatch.delenv("PRODUCTAGENTS_DEBATE_ROUNDS", raising=False)
    calls: list[str] = []

    class _FakeConfig:
        def __init__(self, **_kw):
            pass

        def apply_overrides(self, overrides):
            calls.append(f"overrides:{overrides}")
            os.environ["PRODUCTAGENTS_DEBATE_ROUNDS"] = overrides["debate_rounds"]

        async def load(self):
            calls.append("load")

    monkeypatch.setattr(cli, "ConfigurationService", _FakeConfig)
    cli.main(["--set", "debate_rounds=3"])  # no subcommand -> help, but wiring ran
    assert calls == ["overrides:{'debate_rounds': '3'}", "load"]
    assert os.environ["PRODUCTAGENTS_DEBATE_ROUNDS"] == "3"
