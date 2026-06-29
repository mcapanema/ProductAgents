"""Tests for the JSON-over-stdio IPC adapter."""

import json
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import cast

from productagents.app import ipc
from productagents.platform.events import Event
from productagents.platform.session import Session
from productagents.platform.workflow import Workflow, WorkflowService
from productagents.platform.workspace import Workspace, WorkspaceService


def _collect():
    """Return (emit, sink) where emit is an async fn appending to the sink list."""
    sink: list[dict] = []

    async def emit(message: dict) -> None:
        sink.append(message)

    return emit, sink


class _FakeSessions:
    """Stand-in for SessionService with in-memory rows."""

    def __init__(self, sessions=(), events=None):
        self._sessions = list(sessions)
        self._events = events or {}

    async def list(self):
        return self._sessions

    async def get(self, session_id):
        for s in self._sessions:
            if s.id == session_id:
                return s
        return None

    async def events(self, session_id):
        return self._events.get(session_id, [])


class _FakeWorkspaces:
    def __init__(self, workspaces):
        self._workspaces = list(workspaces)

    def list(self):
        return self._workspaces

    def resolve(self, name=None):
        return self._workspaces[0]


class _FakeConnectors:
    """Stand-in for ConnectorService returning canned reports."""

    def __init__(self, plan=None, health=None, sync=None):
        self._plan = plan
        self._health = health
        self._sync = sync

    def plan(self):
        return self._plan

    async def health(self):
        return self._health

    async def sync(self):
        return self._sync


def _workflows():
    start: Callable[..., tuple[Session, AsyncIterator[Event]]] = cast(
        Callable[..., tuple[Session, AsyncIterator[Event]]],
        lambda *a, **k: None,
    )
    return WorkflowService(
        [
            Workflow(
                name="evaluate_initiative",
                title="Evaluate Initiative",
                description="advisory pipeline",
                start=start,
            )
        ]
    )


async def test_workflows_list_returns_registered_workflows():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 1, "method": "workflows.list"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink == [
        {
            "id": 1,
            "result": [
                {
                    "name": "evaluate_initiative",
                    "title": "Evaluate Initiative",
                    "description": "advisory pipeline",
                }
            ],
        }
    ]


async def test_unknown_method_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 7, "method": "nope.nope"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
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
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions([s]),
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
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink == [{"id": 3, "error": "no such session: missing"}]


async def test_handler_exception_becomes_error_message():
    # sessions.show with no params dict → KeyError on session_id → error, not crash.
    emit, sink = _collect()
    await ipc.handle(
        {"id": 9, "method": "sessions.show"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[0]["id"] == 9
    assert "error" in sink[0]


async def test_workspaces_list_marks_active(tmp_path):
    ws = Workspace(name="default", root=tmp_path)
    emit, sink = _collect()
    await ipc.handle(
        {"id": 4, "method": "workspaces.list"},
        workflows=_workflows(),
        workspaces=cast(WorkspaceService, _FakeWorkspaces([ws])),
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    result = sink[0]["result"]
    assert result[0]["name"] == "default"
    assert result[0]["active"] is True


async def test_workspaces_show_resolves_workspace(tmp_path):
    ws = Workspace(name="default", root=tmp_path)
    emit, sink = _collect()
    await ipc.handle(
        {"id": 5, "method": "workspaces.show", "params": {}},
        workflows=_workflows(),
        workspaces=cast(WorkspaceService, _FakeWorkspaces([ws])),
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[0]["result"]["name"] == "default"
    assert sink[0]["result"]["active"] is True


from productagents.agents import runner as rn  # noqa: E402
from productagents.core.models import (  # noqa: E402
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)
from tests.fakes import fake_workflow_service  # noqa: E402


class _FakeDecisions:
    """Stand-in for DecisionReadService with in-memory rows."""

    def __init__(self, records=(), outcomes=None):
        self._records = list(records)
        self._outcomes = outcomes or {}

    async def list(self):
        return self._records

    async def get(self, decision_id):
        record = next((r for r in self._records if r.decision_id == decision_id), None)
        if record is None:
            return None, []
        return record, self._outcomes.get(decision_id, [])


def _decision(decision_id="d1", title="New API"):
    return DecisionRecord(
        decision_id=decision_id,
        initiative=Initiative(title=title, description=title),
        recommendation=Recommendation(
            recommendation="ship it",
            confidence=0.8,
            rationale="because",
            expected_outcomes=["adoption up"],
        ),
        reports=[],
        timestamp="2026-06-28T00:00:00+00:00",
    )


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
        workflows=fake_workflow_service(runner),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
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
        workflows=fake_workflow_service(runner),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[-1]["id"] == 6
    assert sink[-1]["result"]["status"] == "failed"
    assert isinstance(sink[-1]["result"]["session_id"], str)


async def test_run_unknown_workflow_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 8, "method": "run", "params": {"workflow": "nope", "title": "X"}},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
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
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
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
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
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
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        read_line=read_line,
        write_line=out.append,
    )
    assert [json.loads(line)["id"] for line in out] == [3]


def test_serve_stdio_builds_services_and_serves(monkeypatch):
    captured = {}

    def fake_build_run_service(*, human_in_the_loop=False):
        return _workflows()

    async def fake_serve(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "productagents.app.cli._build_run_service", fake_build_run_service
    )
    monkeypatch.setattr(ipc, "serve", fake_serve)
    monkeypatch.setattr(
        ipc.SessionService, "create", classmethod(lambda cls: "SESSIONS")
    )

    ipc.serve_stdio("acme")

    assert captured["active_name"] == "acme"
    assert captured["sessions"] == "SESSIONS"
    assert isinstance(captured["workflows"], WorkflowService)
    assert isinstance(captured["workspaces"], WorkspaceService)


async def test_decisions_list_returns_summaries():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 10, "method": "decisions.list"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        decisions=_FakeDecisions([_decision("d1")]),
        emit=emit,
    )
    assert sink == [
        {
            "id": 10,
            "result": [
                {
                    "id": "d1",
                    "title": "New API",
                    "recommendation": "ship it",
                    "confidence": 0.8,
                    "created_at": "2026-06-28T00:00:00+00:00",
                }
            ],
        }
    ]


async def test_decisions_show_returns_record_and_outcomes():
    outcome = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["flat"],
        prediction_accuracy=0.4,
        lessons_learned=["scope smaller"],
        reflected_at="2026-06-29T00:00:00+00:00",
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 11, "method": "decisions.show", "params": {"decision_id": "d1"}},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        decisions=_FakeDecisions([_decision("d1")], {"d1": [outcome]}),
        emit=emit,
    )
    result = sink[0]["result"]
    assert sink[0]["id"] == 11
    assert result["record"]["decision_id"] == "d1"
    assert result["record"]["recommendation"]["recommendation"] == "ship it"
    assert result["outcomes"][0]["lessons_learned"] == ["scope smaller"]


async def test_decisions_show_unknown_id_emits_error():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 12, "method": "decisions.show", "params": {"decision_id": "missing"}},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        decisions=_FakeDecisions([_decision("d1")]),
        emit=emit,
    )
    assert sink == [{"id": 12, "error": "no such decision: missing"}]


async def test_connectors_list_returns_names_only():
    from productagents.connectors import ConnectorConfig
    from productagents.platform.connectors import ConnectorPlan

    plan = ConnectorPlan(
        configs={"github": ConnectorConfig(), "jira": ConnectorConfig()},
        problems=["connector 'slack': unknown (not installed)"],
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 20, "method": "connectors.list"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        connectors=_FakeConnectors(plan=plan),
        emit=emit,
    )
    assert sink == [
        {
            "id": 20,
            "result": {
                "connectors": [{"name": "github"}, {"name": "jira"}],
                "problems": ["connector 'slack': unknown (not installed)"],
            },
        }
    ]


async def test_connectors_health_returns_statuses():
    from productagents.connectors import HealthStatus
    from productagents.platform.connectors import HealthReport

    report = HealthReport(
        statuses={"github": HealthStatus(ok=True, detail="reachable")},
        problems=[],
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 21, "method": "connectors.health"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        connectors=_FakeConnectors(health=report),
        emit=emit,
    )
    assert sink == [
        {
            "id": 21,
            "result": {
                "statuses": {"github": {"ok": True, "detail": "reachable"}},
                "problems": [],
            },
        }
    ]


async def test_connectors_sync_returns_results():
    from productagents.connectors import SyncResult
    from productagents.platform.connectors import SyncReport

    report = SyncReport(
        results=[SyncResult(connector="github", written=7, ok=True, error=None)],
        problems=[],
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 22, "method": "connectors.sync"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        connectors=_FakeConnectors(sync=report),
        emit=emit,
    )
    assert sink == [
        {
            "id": 22,
            "result": {
                "results": [
                    {"connector": "github", "written": 7, "ok": True, "error": None}
                ],
                "problems": [],
            },
        }
    ]


async def test_connectors_method_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 23, "method": "connectors.list"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[0]["id"] == 23
    assert "connectors service not available" in sink[0]["error"]


class _FakePrompts:
    """Stand-in for PromptService backed by an in-memory {name: {version: text}}."""

    def __init__(self, prompts):
        self._prompts = prompts

    def names(self):
        return sorted(self._prompts)

    def versions(self, name):
        return sorted(self._prompts[name])

    def read(self, name, version):
        return self._prompts[name][version]

    def diff(self, name, old, new):
        return f"--- {name}@{old}\n+++ {name}@{new}\n"


async def test_prompts_list_returns_names_versions_and_active():
    prompts = _FakePrompts(
        {"strategist": {0: "default", 1: "v1", 2: "v2"}, "judge": {0: "judge"}}
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 30, "method": "prompts.list"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        prompts=prompts,
        emit=emit,
    )
    assert sink == [
        {
            "id": 30,
            "result": [
                {"name": "judge", "versions": [0], "active": 0},
                {"name": "strategist", "versions": [0, 1, 2], "active": 2},
            ],
        }
    ]


async def test_prompts_show_returns_version_text():
    prompts = _FakePrompts({"strategist": {0: "default", 1: "v1", 2: "v2"}})
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 31,
            "method": "prompts.show",
            "params": {"name": "strategist", "version": 2},
        },
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        prompts=prompts,
        emit=emit,
    )
    assert sink == [
        {"id": 31, "result": {"name": "strategist", "version": 2, "text": "v2"}}
    ]


async def test_prompts_diff_returns_unified_diff():
    prompts = _FakePrompts({"strategist": {0: "default", 2: "v2"}})
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 32,
            "method": "prompts.diff",
            "params": {"name": "strategist", "old": 0, "new": 2},
        },
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        prompts=prompts,
        emit=emit,
    )
    assert sink == [
        {
            "id": 32,
            "result": {
                "name": "strategist",
                "old": 0,
                "new": 2,
                "diff": "--- strategist@0\n+++ strategist@2\n",
            },
        }
    ]


async def test_prompts_method_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 33, "method": "prompts.list"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[0]["id"] == 33
    assert "prompts service not available" in sink[0]["error"]


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
        workflows=fake_workflow_service(runner),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
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
        workflows=fake_workflow_service(runner),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        read_line=read_line,
        emit=emit,
    )
    final = [m for m in sink if m.get("event", {}).get("type") == "FinalVerdict"]
    assert final[0]["event"]["payload"]["verdict"] == "approve"


from productagents.app import setup as _setup  # noqa: E402
from tests.fakes import ready_status  # noqa: E402


class _FakeConfig:
    """Stand-in for the app.setup module: canned status + recorded writes.

    Reuses the real pure helpers (provider_for/api_key_var_for/PROVIDERS) so the
    derivation under test is the real one; only check_config/write_env are faked
    to stay offline (no real .env, no os.environ mutation)."""

    PROVIDERS = _setup.PROVIDERS
    provider_for = staticmethod(_setup.provider_for)
    api_key_var_for = staticmethod(_setup.api_key_var_for)

    def __init__(self, status):
        self._status = status
        self.written: list[tuple[dict, object]] = []

    def check_config(self):
        return self._status

    def write_env(self, values, *, dotenv_path=None):
        self.written.append((dict(values), dotenv_path))
        return str(dotenv_path or ".env")


async def test_config_get_returns_status_and_providers():
    config = _FakeConfig(ready_status())
    emit, sink = _collect()
    await ipc.handle(
        {"id": 40, "method": "config.get"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        config=config,
        emit=emit,
    )
    result = sink[0]["result"]
    assert result["model"] == "anthropic:claude-sonnet-4-6"
    assert result["provider"] == "anthropic"
    assert result["key_present"] is True
    anthropic = next(p for p in result["providers"] if p["id"] == "anthropic")
    assert anthropic["key_var"] == "ANTHROPIC_API_KEY"
    assert anthropic["label"] == "Anthropic"


async def test_config_set_writes_workspace_env_and_returns_status(tmp_path):
    config = _FakeConfig(ready_status())
    # Workspace takes only name + root (a Path); env_file is root/".env".
    ws = Workspace(name="default", root=tmp_path)
    workspaces = cast(WorkspaceService, _FakeWorkspaces([ws]))
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 41,
            "method": "config.set",
            "params": {"model": "openai:gpt-4o", "api_key": "sk-test"},
        },
        workflows=_workflows(),
        workspaces=workspaces,
        active_name="default",
        sessions=_FakeSessions(),
        config=config,
        emit=emit,
    )
    values, dotenv_path = config.written[0]
    assert values["PRODUCTAGENTS_MODEL"] == "openai:gpt-4o"
    assert values["OPENAI_API_KEY"] == "sk-test"
    assert "PRODUCTAGENTS_MODEL_PROVIDER" not in values  # derivable from prefix
    assert dotenv_path == str(tmp_path / ".env")
    assert sink[0]["result"]["model"] == "anthropic:claude-sonnet-4-6"


async def test_config_set_skips_blank_api_key():
    config = _FakeConfig(ready_status())
    emit, _sink = _collect()
    await ipc.handle(
        {
            "id": 42,
            "method": "config.set",
            "params": {"model": "openai:gpt-4o", "api_key": ""},
        },
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        config=config,
        emit=emit,
    )
    values, _ = config.written[0]
    assert "OPENAI_API_KEY" not in values  # never write a blank key


async def test_config_method_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 43, "method": "config.get"},
        workflows=_workflows(),
        workspaces=None,
        active_name="default",
        sessions=_FakeSessions(),
        emit=emit,
    )
    assert sink[0]["id"] == 43
    assert "config service not available" in sink[0]["error"]
