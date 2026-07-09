"""Tests for the JSON-over-stdio IPC adapter (core: sessions/workspaces/run/serve
streaming, reflection, preferences). Area-specific suites live in the sibling
``test_ipc_<area>.py`` files; shared fakes live in ``tests/_ipc_helpers.py``.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import cast

from productagents.agents import runner as rn
from productagents.app import ipc
from productagents.core.models import OutcomeRecord, Recommendation
from productagents.platform.session import Session
from productagents.platform.workflow import WorkflowService
from productagents.platform.workspace import WorkspaceService
from tests._ipc_helpers import _collect, _FakeSessions, _workflows
from tests.fakes import fake_workflow_service


class _FakeWorkspaces:
    def __init__(self, names=("default",), active="default"):
        self._names = list(names)
        self.active = active

    async def list(self):
        return [{"name": n, "created_at": "t"} for n in self._names]

    async def get(self, name):
        return {"name": name, "created_at": "t"} if name in self._names else None

    async def create(self, name):
        from productagents.platform.workspace import WorkspaceError

        if name in self._names:
            raise WorkspaceError(f"workspace already exists: {name}")
        self._names.append(name)
        return {"name": name, "created_at": "t"}

    async def set_active(self, name):
        from productagents.platform.workspace import WorkspaceError

        if name not in self._names:
            raise WorkspaceError(f"no such workspace: {name}")
        self.active = name
        return {"name": name, "created_at": "t"}

    def home(self):  # for workspaces.show paths
        from pathlib import Path

        from productagents.platform.workspace import SharedHome

        return SharedHome(root=Path("/tmp/pa-home"))

    def prompts_dir(self, name):
        return self.home().prompts_root / name

    async def rename(self, old, new):
        from productagents.platform.workspace import WorkspaceError

        if old not in self._names:
            raise WorkspaceError(f"no such workspace: {old}")
        if new in self._names:
            raise WorkspaceError(f"workspace already exists: {new}")
        self._names[self._names.index(old)] = new
        if self.active == old:
            self.active = new
        return {"name": new, "created_at": "t"}


async def test_unknown_method_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 7, "method": "nope.nope"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink == [{"id": 7, "error": "unknown method: 'nope.nope'"}]


async def test_sessions_list_returns_rows():
    emit, sink = _collect()
    s = Session(
        id="abc",
        workflow="evaluate_initiative",
        status="finished",
        created_at=datetime(2026, 6, 28, tzinfo=UTC),
    )
    await ipc.handle(
        {"id": 2, "method": "sessions.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions([s]),
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 2,
            "result": [
                {
                    "id": "abc",
                    "workflow": "evaluate_initiative",
                    "status": "finished",
                    "created_at": "2026-06-28T00:00:00+00:00",
                }
            ],
        }
    ]


async def test_sessions_show_unknown_id_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 3, "method": "sessions.show", "params": {"session_id": "missing"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink == [{"id": 3, "error": "no such session: missing"}]


async def test_handler_exception_becomes_error_message():
    # sessions.show with no params dict → KeyError on session_id → error, not crash.
    emit, sink = _collect()
    await ipc.handle(
        {"id": 9, "method": "sessions.show"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 9
    assert "error" in sink[0]


async def _real_workspaces(tmp_path):
    """A real, async WorkspaceService over a fresh in-memory engine."""
    from productagents.knowledge.repositories.sqlmodel.engine import make_engine
    from productagents.memory.store import create_all
    from productagents.platform.workspace import SharedHome

    engine = make_engine("sqlite+aiosqlite:///:memory:")
    await create_all(engine)
    return WorkspaceService(home=SharedHome(root=tmp_path), engine=engine)


async def test_workspaces_list_marks_active():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 4, "method": "workspaces.list"},
        {
            "workflows": _workflows(),
            "workspaces": _FakeWorkspaces(),
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    result = sink[0]["result"]
    assert result[0]["name"] == "default"
    assert result[0]["active"] is True


async def test_workspaces_show_resolves_workspace():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 5, "method": "workspaces.show", "params": {}},
        {
            "workflows": _workflows(),
            "workspaces": _FakeWorkspaces(),
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["result"]["name"] == "default"
    assert sink[0]["result"]["active"] is True
    assert sink[0]["result"]["prompts_dir"].endswith("prompts/default")


async def test_workspaces_show_unknown_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 5, "method": "workspaces.show", "params": {"name": "nope"}},
        {
            "workflows": _workflows(),
            "workspaces": _FakeWorkspaces(),
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert "error" in sink[0]
    assert "no such workspace" in sink[0]["error"]


async def test_workspaces_create_returns_new_workspace(tmp_path):
    emit, sink = _collect()
    await ipc.handle(
        {"id": 7, "method": "workspaces.create", "params": {"name": "acme"}},
        {
            "workflows": _workflows(),
            "workspaces": await _real_workspaces(tmp_path),
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 7
    assert sink[0]["result"]["name"] == "acme"
    assert sink[0]["result"]["active"] is False


async def test_workspaces_create_duplicate_emits_error(tmp_path):
    svc = await _real_workspaces(tmp_path)
    await svc.create("acme")
    emit, sink = _collect()
    await ipc.handle(
        {"id": 8, "method": "workspaces.create", "params": {"name": "acme"}},
        {
            "workflows": _workflows(),
            "workspaces": svc,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert "error" in sink[0]
    assert "already exists" in sink[0]["error"]


async def test_workspaces_use_switches_marker(tmp_path):
    svc = await _real_workspaces(tmp_path)
    await svc.create("acme")
    emit, sink = _collect()
    await ipc.handle(
        {"id": 9, "method": "workspaces.use", "params": {"name": "acme"}},
        {
            "workflows": _workflows(),
            "workspaces": svc,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink == [{"id": 9, "result": {"name": "acme", "active": True}}]
    assert svc.active_name() == "acme"


async def test_workspaces_use_unknown_emits_error(tmp_path):
    emit, sink = _collect()
    await ipc.handle(
        {"id": 10, "method": "workspaces.use", "params": {"name": "nope"}},
        {
            "workflows": _workflows(),
            "workspaces": await _real_workspaces(tmp_path),
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert "error" in sink[0]
    assert "no such workspace" in sink[0]["error"]


async def test_workspaces_use_switches_live():
    """use -> config.switch + rebuild swap the dict; the NEXT request sees it."""
    switched = []

    class _FakeConfig:
        async def switch(self, name):
            switched.append(name)

    ws = _FakeWorkspaces(names=("default", "acme"))
    config = _FakeConfig()
    rebuild_calls = []
    post_switch_session = Session(
        id="post-switch-row",
        workflow="evaluate_initiative",
        status="finished",
        created_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    def fake_rebuild(name, *, config=None):
        rebuild_calls.append((name, config))
        return {
            "workflows": _workflows(),
            "workspaces": object(),  # must be popped, never installed
            "active_name": name,
            "sessions": _FakeSessions([post_switch_session]),
            "rebuild": fake_rebuild,
        }

    services = {
        "workflows": _workflows(),
        "workspaces": ws,
        "active_name": "default",
        "sessions": _FakeSessions(),
        "config": config,
        "rebuild": fake_rebuild,
    }
    emit, sink = _collect()
    await ipc.handle(
        {"id": 1, "method": "workspaces.use", "params": {"name": "acme"}},
        services,
        emit=emit,
    )
    assert sink == [{"id": 1, "result": {"name": "acme", "active": True}}]
    assert switched == ["acme"]
    assert rebuild_calls == [("acme", config)]
    assert services["active_name"] == "acme"
    assert ws.active == "acme"
    assert services["workspaces"] is ws  # instance identity preserved

    # The very next request against the SAME dict sees the rebuilt scope.
    await ipc.handle({"id": 2, "method": "sessions.list"}, services, emit=emit)
    assert sink[1]["id"] == 2
    assert [row["id"] for row in sink[1]["result"]] == ["post-switch-row"]


async def test_workspaces_use_switch_failure_leaves_marker_untouched():
    """config.switch blowing up -> {id, error}, marker and active_name unchanged."""

    class _BoomConfig:
        async def switch(self, name):
            raise RuntimeError("db down")

    ws = _FakeWorkspaces(names=("default", "acme"))
    services = {
        "workflows": _workflows(),
        "workspaces": ws,
        "active_name": "default",
        "sessions": _FakeSessions(),
        "config": _BoomConfig(),
    }
    emit, sink = _collect()
    await ipc.handle(
        {"id": 3, "method": "workspaces.use", "params": {"name": "acme"}},
        services,
        emit=emit,
    )
    assert sink[0]["id"] == 3
    assert "db down" in sink[0]["error"]
    assert ws.active == "default"  # marker never flipped
    assert services["active_name"] == "default"


async def test_workspaces_use_rebuild_failure_switches_config_back():
    """A rebuild failure AFTER config.switch succeeded must not leave a torn
    switch: config gets switched back to the old workspace, and the marker /
    active_name (which move last) are untouched."""
    switched = []

    class _FlakyConfig:
        async def switch(self, name):
            switched.append(name)

    ws = _FakeWorkspaces(names=("default", "acme"))

    def boom_rebuild(name, *, config=None):
        raise RuntimeError("rebuild exploded")

    services = {
        "workflows": _workflows(),
        "workspaces": ws,
        "active_name": "default",
        "sessions": _FakeSessions(),
        "config": _FlakyConfig(),
        "rebuild": boom_rebuild,
    }
    emit, sink = _collect()
    await ipc.handle(
        {"id": 4, "method": "workspaces.use", "params": {"name": "acme"}},
        services,
        emit=emit,
    )
    assert sink[0]["id"] == 4
    assert "rebuild exploded" in sink[0]["error"]
    assert switched == ["acme", "default"]  # switched forward, then restored
    assert ws.active == "default"  # marker never flipped
    assert services["active_name"] == "default"


async def test_workspaces_rename_active_runs_switch_tail():
    switched, rebuilt = [], []

    class _FakeConfig:
        async def switch(self, name):
            switched.append(name)

    ws = _FakeWorkspaces(names=("default", "other"))

    def fake_rebuild(name, config=None):
        rebuilt.append((name, config))
        return {"workspaces": object(), "sessions": _FakeSessions()}

    config = _FakeConfig()
    services = {
        "workflows": _workflows(),
        "workspaces": ws,
        "active_name": "default",
        "sessions": _FakeSessions(),
        "config": config,
        "rebuild": fake_rebuild,
    }
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 1,
            "method": "workspaces.rename",
            "params": {"name": "default", "new_name": "main"},
        },
        services,
        emit=emit,
    )
    assert sink == [
        {"id": 1, "result": {"name": "main", "created_at": "t", "active": True}}
    ]
    assert switched == ["main"]
    assert rebuilt == [("main", config)]
    assert services["active_name"] == "main"
    assert services["workspaces"] is ws  # identity preserved through rebuild


async def test_workspaces_rename_nonactive_skips_switch_tail():
    switched = []

    class _FakeConfig:
        async def switch(self, name):
            switched.append(name)

    ws = _FakeWorkspaces(names=("default", "other"))
    services = {
        "workflows": _workflows(),
        "workspaces": ws,
        "active_name": "default",
        "sessions": _FakeSessions(),
        "config": _FakeConfig(),
    }
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 2,
            "method": "workspaces.rename",
            "params": {"name": "other", "new_name": "renamed"},
        },
        services,
        emit=emit,
    )
    assert sink == [
        {"id": 2, "result": {"name": "renamed", "created_at": "t", "active": False}}
    ]
    assert switched == []
    assert services["active_name"] == "default"


async def test_workspaces_rename_duplicate_emits_error():
    ws = _FakeWorkspaces(names=("default", "other"))
    services = {
        "workflows": _workflows(),
        "workspaces": ws,
        "active_name": "default",
        "sessions": _FakeSessions(),
    }
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 3,
            "method": "workspaces.rename",
            "params": {"name": "other", "new_name": "default"},
        },
        services,
        emit=emit,
    )
    assert "error" in sink[0]
    assert "already exists" in sink[0]["error"]


def _rec(text="ship it"):
    return Recommendation(
        recommendation=text,
        confidence=0.8,
        rationale="because",
        expected_outcomes=["outcome"],
        failed=False,
    )


async def test_run_streams_events_then_finished_result():
    async def runner(initiative, evidence, *, approver=None):
        yield rn.ProgressEvent(node="market", message="scanning")
        yield rn.FinishedEvent(
            recommendation=_rec(),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
            prior_lessons=[],
            judgment=None,
        )

    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 5,
            "method": "run",
            "params": {
                "workflow": "evaluate_initiative",
                "title": "New API",
                "evidence": "sample",
            },
        },
        {
            "workflows": fake_workflow_service(runner),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )

    event_msgs = [m for m in sink if "event" in m]
    assert event_msgs[0]["event"]["type"] == "SessionStarted"
    assert any(m["event"]["type"] == "NodeProgress" for m in event_msgs)
    terminal = sink[-1]
    assert terminal["id"] == 5
    assert terminal["result"]["status"] == "finished"
    assert isinstance(terminal["result"]["session_id"], str)


async def test_run_reports_failed_status_on_abort():
    async def runner(initiative, evidence, *, approver=None):
        yield rn.RunAbortedEvent(node="market", category="rate_limit", message="429")

    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 6,
            "method": "run",
            "params": {
                "workflow": "evaluate_initiative",
                "title": "X",
                "evidence": "sample",
            },
        },
        {
            "workflows": fake_workflow_service(runner),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[-1]["id"] == 6
    assert sink[-1]["result"]["status"] == "failed"
    assert isinstance(sink[-1]["result"]["session_id"], str)


async def test_run_unknown_workflow_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 8, "method": "run", "params": {"workflow": "nope", "title": "X"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 8
    assert "error" in sink[0]


def _line_reader(lines):
    """Async read_line yielding each line then '' (EOF) forever."""
    queue = list(lines)

    async def read_line():
        return queue.pop(0) if queue else ""

    return read_line


async def test_serve_dispatches_each_line_until_eof():
    out: list[str] = []
    read_line = _line_reader(
        [
            json.dumps({"id": 1, "method": "workflows.list"}) + "\n",
            json.dumps({"id": 2, "method": "sessions.list"}) + "\n",
        ]
    )
    await ipc.serve(
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        read_line=read_line,
        write_line=out.append,
    )
    parsed = [json.loads(line) for line in out]
    assert [m["id"] for m in parsed] == [1, 2]
    assert parsed[1]["result"] == []  # no sessions


async def test_serve_reports_invalid_json_and_continues():
    out: list[str] = []
    read_line = _line_reader(
        [
            "not json\n",
            json.dumps({"id": 2, "method": "workflows.list"}) + "\n",
        ]
    )
    await ipc.serve(
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        read_line=read_line,
        write_line=out.append,
    )
    parsed = [json.loads(line) for line in out]
    assert parsed[0]["id"] is None
    assert "invalid json" in parsed[0]["error"]
    assert parsed[1]["id"] == 2  # loop kept going


async def test_serve_skips_blank_lines():
    out: list[str] = []
    read_line = _line_reader(
        ["\n", "   \n", json.dumps({"id": 3, "method": "workflows.list"}) + "\n"]
    )
    await ipc.serve(
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        read_line=read_line,
        write_line=out.append,
    )
    assert [json.loads(line)["id"] for line in out] == [3]


def test_serve_stdio_builds_services_and_serves(monkeypatch):
    captured = {}

    async def fake_serve(services, **kwargs):
        captured.update(services)
        captured.update(kwargs)

    monkeypatch.setattr(
        ipc.WorkflowService,
        "production",
        classmethod(lambda cls, **_kw: _workflows()),
    )
    monkeypatch.setattr(ipc, "serve", fake_serve)
    monkeypatch.setattr(
        ipc.SessionService,
        "create",
        classmethod(lambda cls, workspace="default": "SESSIONS"),
    )

    ipc.serve_stdio("acme")

    assert captured["active_name"] == "acme"
    assert captured["sessions"] == "SESSIONS"
    assert isinstance(captured["workflows"], WorkflowService)
    assert isinstance(captured["workspaces"], WorkspaceService)


async def test_run_with_approval_reads_decision_and_resumes():
    async def runner(initiative, evidence, *, approver=None):
        yield rn.ProgressEvent(node="governance", message="awaiting approval")
        assert approver is not None
        decision = await approver(None)  # the IPC approver reads the client's line
        yield rn.FinalVerdictEvent(
            verdict=decision.verdict, rationale=decision.rationale, decided_by="human"
        )
        yield rn.FinishedEvent(
            recommendation=_rec(),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
            prior_lessons=[],
            judgment=None,
        )

    read_line = _line_reader(
        [
            json.dumps(
                {
                    "id": 99,
                    "method": "approve",
                    "params": {"verdict": "reject", "rationale": "too risky"},
                }
            )
        ]
    )
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 5,
            "method": "run",
            "params": {
                "workflow": "evaluate_initiative",
                "title": "New API",
                "evidence": "sample",
                "approval": True,
            },
        },
        {
            "workflows": fake_workflow_service(runner),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        read_line=read_line,
        emit=emit,
    )

    # The approve message was acked under its own id.
    assert {"id": 99, "result": {"ok": True}} in sink
    # The human decision drove the FinalVerdict the run emitted.
    final = [m for m in sink if m.get("event", {}).get("type") == "FinalVerdict"]
    assert final
    assert final[0]["event"]["payload"]["verdict"] == "reject"
    assert sink[-1] == {
        "id": 5,
        "result": {
            "status": "finished",
            "session_id": sink[-1]["result"]["session_id"],
        },
    }


async def test_run_approval_defaults_invalid_verdict_to_approve():
    async def runner(initiative, evidence, *, approver=None):
        assert approver is not None
        decision = await approver(None)
        yield rn.FinalVerdictEvent(
            verdict=decision.verdict, rationale=decision.rationale, decided_by="human"
        )
        yield rn.FinishedEvent(
            recommendation=_rec(),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
            prior_lessons=[],
            judgment=None,
        )

    read_line = _line_reader(
        [json.dumps({"id": 1, "method": "approve", "params": {"verdict": "garbage"}})]
    )
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 5,
            "method": "run",
            "params": {
                "workflow": "evaluate_initiative",
                "title": "X",
                "approval": True,
            },
        },
        {
            "workflows": fake_workflow_service(runner),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        read_line=read_line,
        emit=emit,
    )
    final = [m for m in sink if m.get("event", {}).get("type") == "FinalVerdict"]
    assert final[0]["event"]["payload"]["verdict"] == "approve"


class _FakeReflection:
    def __init__(self, *, outcome=None, missing=False):
        self._outcome = outcome
        self._missing = missing

    async def reflect_on(self, decision_id, note):
        if self._missing:
            raise LookupError(f"no such decision: {decision_id}")
        return self._outcome


def _outcome():
    return OutcomeRecord(
        decision_id="dec-1",
        actual_outcomes=["slow adoption"],
        prediction_accuracy=0.4,
        lessons_learned=["validate demand earlier"],
        reflected_at="2026-06-20T12:00:00+00:00",
    )


async def test_reflection_record_persists_and_returns_outcome():
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 7,
            "method": "reflection.record",
            "params": {"decision_id": "dec-1", "note": "shipped"},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "reflection": _FakeReflection(outcome=_outcome()),
        },
        emit=emit,
    )
    assert sink == [{"id": 7, "result": _outcome().model_dump(mode="json")}]


async def test_reflection_record_unknown_decision_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 8,
            "method": "reflection.record",
            "params": {"decision_id": "nope", "note": "x"},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "reflection": _FakeReflection(missing=True),
        },
        emit=emit,
    )
    assert sink == [{"id": 8, "error": "no such decision: nope"}]


async def test_reflection_record_unavailable_when_service_missing():
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 9,
            "method": "reflection.record",
            "params": {"decision_id": "d", "note": "x"},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 9
    assert "reflection service not available" in sink[0]["error"]


class _CancellableWorkflows:
    """run() streams SessionStarted then blocks until cancel() fires."""

    def __init__(self):
        self._fire = asyncio.Event()
        self.cancelled = None

    def run(self, name, initiative, evidence, *, approver=None):
        session = Session(id="s-cancel", workflow="evaluate_initiative")
        return session, self._stream(session)

    async def _stream(self, session):
        from productagents.platform import events as ev

        yield ev.SessionStarted(session_id=session.id, seq=0, workflow=session.workflow)
        await self._fire.wait()
        yield ev.SessionCancelled(session_id=session.id, seq=1)

    def cancel(self, session_id):
        self.cancelled = session_id
        self._fire.set()
        return True


async def test_run_cancel_mid_stream_reports_cancelled():
    wf = _CancellableWorkflows()
    read_line = _line_reader(
        [
            json.dumps(
                {"id": 77, "method": "run.cancel", "params": {"session_id": "s-cancel"}}
            )
        ]
    )
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 5,
            "method": "run",
            "params": {"workflow": "evaluate_initiative", "title": "X"},
        },
        {
            "workflows": cast(WorkflowService, wf),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        read_line=read_line,
        emit=emit,
    )
    assert wf.cancelled == "s-cancel"
    assert {"id": 77, "result": {"ok": True}} in sink
    types = [m["event"]["type"] for m in sink if "event" in m]
    assert "SessionCancelled" in types
    assert sink[-1] == {
        "id": 5,
        "result": {"status": "cancelled", "session_id": "s-cancel"},
    }


async def test_run_cancel_standalone_when_no_active_run():
    # run.cancel with no in-flight run goes through the dispatch table.
    emit, sink = _collect()
    await ipc.handle(
        {"id": 6, "method": "run.cancel", "params": {"session_id": "ghost"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink == [{"id": 6, "result": {"ok": False}}]


class _FakePreferences:
    def __init__(self):
        self.values = {}

    async def all(self):
        return dict(self.values)

    async def set(self, key, value):
        if key != "theme":
            raise ValueError(f"unknown preference: {key!r}")
        self.values[key] = value
        return dict(self.values)


async def test_preferences_get_and_set():
    prefs = _FakePreferences()
    emit, sink = _collect()
    await ipc.handle(
        {"id": 60, "method": "preferences.set", "params": {"theme": "dark"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "preferences": prefs,
        },
        emit=emit,
    )
    assert sink[0]["result"] == {"theme": "dark"}
    await ipc.handle(
        {"id": 61, "method": "preferences.get"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "preferences": prefs,
        },
        emit=emit,
    )
    assert sink[1]["result"] == {"theme": "dark"}


async def test_preferences_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 62, "method": "preferences.get"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert "preferences service not available" in sink[0]["error"]
