"""JSON-over-stdio IPC client of the ProductAgents Application Layer.

A presentation adapter for out-of-process clients (the future Tauri GUI). It
speaks newline-delimited JSON on stdin/stdout: one request object per input
line, one or more response objects per output line, each echoing the request
``id``. Like ``cli.py`` it imports only ``platform`` + ``core`` + sibling
``app`` modules and drives the same Application Services — proving the
Application Layer is sufficient to run the platform across a process boundary.

ponytail: NDJSON over stdio, not HTTP. The vision is local-first with no
remote APIs (docs/notes/v3-concepts.md), and Tauri launches the Python
backend as a child process it talks to over stdio. The product client/server
split stays deferred; the only non-stdio transport is ``devbridge.py``, a
dev-only localhost WebSocket that reuses ``handle`` + ``build_services`` for
browser/Playwright UI testing.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from productagents.core.models import HumanDecision, Initiative
from productagents.platform import events as ev
from productagents.platform.configuration import ConfigurationService
from productagents.platform.connector_service import ConnectorService
from productagents.platform.decision_read_service import DecisionReadService
from productagents.platform.memory_service import MemoryService
from productagents.platform.preference_service import PreferenceService
from productagents.platform.prompt_service import PromptService
from productagents.platform.serialization import serialize_event
from productagents.platform.session import Session
from productagents.platform.session_service import SessionService
from productagents.platform.workflow import Workflow, WorkflowService
from productagents.platform.workspace import WorkspaceService

logger = logging.getLogger(__name__)

Emit = Callable[[dict], Awaitable[None]]


def _build_workflows(active_name: str, *, human_in_the_loop: bool) -> WorkflowService:
    """Build the run service, degrading to a model-less one if no key is set.

    A freshly installed app has no API key until the user enters one in Settings,
    so ``get_model()`` raises at sidecar startup. We must not crash: the GUI needs
    the read methods + ``config.set`` to reach a usable state. Falling back to a
    ``WorkflowService`` over ``model=None`` keeps ``list`` working (so the
    Workflows panel renders); a ``run`` then degrades to a ``SessionFailed`` event
    until a key is configured and the app restarted.
    """
    from productagents.app.cli import _build_run_service, make_recorder

    try:
        return _build_run_service(
            human_in_the_loop=human_in_the_loop, workspace=active_name
        )
    except Exception:  # noqa: BLE001 — degraded mode; any failure (missing key, bad config) must not crash the sidecar
        logger.warning(
            "model unavailable; runs disabled until an API key is set", exc_info=True
        )
        return WorkflowService.for_model(
            None,
            recorder=make_recorder(workspace=active_name),
            human_in_the_loop=human_in_the_loop,
            workspace=active_name,
        )


def _build_reflection(active_name: str):
    """ReflectionService for the GUI, or None if no model is available yet."""
    from productagents.platform.llm import get_model
    from productagents.platform.reflection_service import ReflectionService

    try:
        return ReflectionService.for_model(get_model(), workspace=active_name)
    except Exception:  # noqa: BLE001
        logger.warning(
            "model unavailable; reflection disabled until an API key is set",
            exc_info=True,
        )
        return None


def build_services(
    active_name: str, *, config: ConfigurationService | None = None
) -> dict:
    """Construct the production Application Services the IPC adapters dispatch to.

    Shared by ``serve_stdio`` (stdio transport) and the dev WebSocket bridge
    (``devbridge.py``) so both expose the identical surface. Builds a real
    model-backed WorkflowService (so ``run`` works), plus the workspace + session
    + decision read services. The returned dict is exactly what ``serve`` /
    ``handle`` read from at dispatch time.

    ``config`` lets a caller (``cli.main``) hand in the single, already-``load()``ed
    ``ConfigurationService`` for this process, so its ``_seeded``/``_overrides``
    state (and thus ``settings_origins()``) reflects the real startup precedence
    chain instead of a fresh instance's empty state. Falls back to a fresh
    instance for tests/back-compat.

    The ``"rebuild"`` entry is this function itself — the live ``workspaces.use``
    switch calls back through it to re-materialize every scoped service against
    the new active workspace.

    ponytail: the model is built up front, so even read methods need a key. Make
    the WorkflowService lazy-on-first-run only if a client must browse without one.
    """
    return {
        "workflows": _build_workflows(active_name, human_in_the_loop=True),
        "workspaces": WorkspaceService(),
        "active_name": active_name,
        "sessions": SessionService.create(active_name),
        "decisions": DecisionReadService.create(active_name),
        "connectors": ConnectorService(workspace=active_name),
        "prompts": PromptService.create(active_name),
        "config": config
        if config is not None
        else ConfigurationService(active_name=active_name),
        "preferences": PreferenceService(),
        "reflection": _build_reflection(active_name),
        "memory": MemoryService.create(active_name),
        "rebuild": build_services,
    }


def serve_stdio(
    active_name: str, *, config: ConfigurationService | None = None
) -> None:
    """Build production services and serve the stdio loop until EOF.

    Backs ``productagents ipc``. The Tauri shell (Phase 8) spawns this as its
    sidecar.
    """
    asyncio.run(serve(build_services(active_name, config=config)))


async def _run(
    rid,
    params: dict,
    *,
    workflows: WorkflowService,
    read_line: Callable[[], Awaitable[str]] | None,
    emit: Emit,
) -> None:
    """Run a workflow and stream its events, then a terminal status result.

    When ``params['approval']`` is truthy the run is human-in-the-loop: the graph
    pauses at governance, the platform streams an ``ApprovalRequested`` event, and
    the injected approver reads the client's next ``approve`` line as the decision.
    A ``SessionFailed`` event flips the terminal status to ``"failed"``.
    """
    title = params["title"]
    initiative = Initiative(title=title, description=title)

    approver = None
    if params.get("approval"):
        if read_line is None:
            await emit(
                {"id": rid, "error": "approval requires an interactive transport"}
            )
            return

        async def approver(
            _request,
        ):  # advisory already streamed; read client's decision
            return await _ipc_approve(read_line, emit)

    session, stream = workflows.run(
        params["workflow"], initiative, params.get("evidence", ""), approver=approver
    )

    # Concurrent cancel watcher — only for non-approval runs (HITL already owns
    # the control line via its approver; two stdin readers would race).
    watch = None
    if (
        not params.get("approval")
        and read_line is not None
        and hasattr(workflows, "cancel")
    ):
        watch = asyncio.ensure_future(
            _watch_cancel(session.id, workflows, read_line, emit)
        )

    status = "finished"
    try:
        async for event in stream:
            if isinstance(event, ev.SessionFailed):
                status = "failed"
            elif isinstance(event, ev.SessionCancelled):
                status = "cancelled"
            etype, payload = serialize_event(event)
            await emit({"id": rid, "event": {"type": etype, "payload": payload}})
    finally:
        if watch is not None:
            watch.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watch
    await emit({"id": rid, "result": {"status": status, "session_id": session.id}})


async def _ipc_approve(
    read_line: Callable[[], Awaitable[str]], emit: Emit
) -> HumanDecision:
    """Read the client's next message as a HITL approval decision and ack it.

    The serve loop is paused inside the running workflow, so reading the next
    line *is* the approval (the documented seam: server emits ApprovalRequested,
    client sends `approve`). A malformed/invalid verdict degrades to "approve" so
    a bad message can't abort the run.
    """
    raw = await read_line()
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError, TypeError:
        msg = {}
    p = msg.get("params") or {}
    verdict = p.get("verdict", "approve")
    if verdict not in ("approve", "reject", "request_analysis"):
        verdict = "approve"
    if msg.get("id") is not None:
        await emit({"id": msg["id"], "result": {"ok": True}})
    return HumanDecision(verdict=verdict, rationale=p.get("rationale", ""))


async def _watch_cancel(
    session_id: str,
    workflows: WorkflowService,
    read_line: Callable[[], Awaitable[str]],
    emit: Emit,
) -> None:
    """Read control lines while a run streams; act on a run.cancel.

    The serve loop is parked in _run, so this is the sole stdin consumer during
    a (non-approval) run. ponytail: only run.cancel is honored here; any other
    line during an active run violates the single-in-flight protocol and is
    ignored.
    """
    while True:
        raw = await read_line()
        if not raw:
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError, TypeError:
            continue
        if msg.get("method") == "run.cancel":
            incoming_sid = (msg.get("params") or {}).get("session_id", "")
            if incoming_sid != session_id:
                continue  # not for this session, ignore
            ok = workflows.cancel(session_id)
            if msg.get("id") is not None:
                await emit({"id": msg["id"], "result": {"ok": ok}})
            return


def _workflow_dict(w: Workflow) -> dict:
    return {"name": w.name, "title": w.title, "description": w.description}


def _session_dict(s: Session) -> dict:
    return {
        "id": s.id,
        "workflow": s.workflow,
        "status": s.status,
        "created_at": s.created_at.isoformat(),
    }


def _lesson_dict(lesson) -> dict:
    return {
        "decision_id": lesson.decision_id,
        "title": lesson.title,
        "text": lesson.text,
        "validated": lesson.validated,
        "prediction_accuracy": lesson.prediction_accuracy,
    }


def _decision_summary(d) -> dict:
    return {
        "id": d.decision_id,
        "title": d.initiative.title,
        "recommendation": d.recommendation.recommendation,
        "confidence": d.recommendation.confidence,
        "created_at": d.timestamp,
    }


def _decision_detail(record, outcomes) -> dict:
    return {
        "record": record.model_dump(mode="json"),
        "outcomes": [o.model_dump(mode="json") for o in outcomes],
    }


def _connector_plan_dict(plan) -> dict:
    # Names only — plan.configs holds resolved secrets that must not leak.
    return {
        "connectors": [{"name": name} for name in sorted(plan.configs)],
        "problems": plan.problems,
    }


def _health_dict(report) -> dict:
    return {
        "statuses": {
            name: {"ok": s.ok, "detail": s.detail}
            for name, s in report.statuses.items()
        },
        "problems": report.problems,
    }


def _sync_dict(report) -> dict:
    return {
        "results": [
            {
                "connector": r.connector,
                "written": r.written,
                "ok": r.ok,
                "error": r.error,
            }
            for r in report.results
        ],
        "problems": report.problems,
    }


def _prompt_summary(prompts, name: str) -> dict:
    # versions() is [0, *sorted overrides], so the last element is the active version.
    versions = prompts.versions(name)
    return {"name": name, "versions": versions, "active": versions[-1]}


def _config_dict(config) -> dict:
    status = config.status()
    return {
        "model": status.model,
        "provider": status.provider,
        "key_var": status.key_var,
        "key_present": status.key_present,
        "problems": status.problems,
        "settings": config.settings(),
        "origins": config.settings_origins(),
        "providers": [
            {
                "id": pid,
                "label": info.label,
                "key_var": info.key_var,
                "default_model": info.default_model,
            }
            for pid, info in config.providers().items()
        ],
    }


async def handle(
    request: dict,
    services: dict,
    *,
    read_line: Callable[[], Awaitable[str]] | None = None,
    emit: Emit,
) -> None:
    """Dispatch one request, emitting one or more response messages.

    ``services`` is a mutable dict (see ``build_services``) read at dispatch
    time — ``workspaces.use`` mutates it in place, so the very next request
    sees the freshly rebuilt scope.

    Every emitted message echoes ``request['id']``. Every method except ``run``
    emits a single ``result``; any failure becomes one ``error`` message so the
    serve loop never dies on a single bad request.
    """
    rid = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}
    workflows: WorkflowService = services["workflows"]
    workspaces: WorkspaceService | None = services.get("workspaces")
    active_name: str = services["active_name"]
    sessions = services["sessions"]
    decisions: Any = services.get("decisions")
    connectors: Any = services.get("connectors")
    prompts: Any = services.get("prompts")
    config: Any = services.get("config")
    preferences: Any = services.get("preferences")
    reflection: Any = services.get("reflection")
    memory: Any = services.get("memory")
    try:
        # ``run`` streams multiple events before its terminal result — kept as an
        # explicit branch rather than forced into the uniform request/response table.
        if method == "run":
            await _run(rid, params, workflows=workflows, read_line=read_line, emit=emit)
            return

        # Dispatch table: each handler is a closure capturing the outer service vars
        # and (rid, emit) so it can emit directly. Exceptions bubble to the outer
        # except so one bad request never kills the loop.

        async def _workflows_list(_p: dict) -> None:
            wfs = [_workflow_dict(w) for w in workflows.list()]
            await emit({"id": rid, "result": wfs})

        async def _workflows_show(p: dict) -> None:
            name = p.get("name", "")
            w = workflows.get(name)
            if w is None:
                await emit({"id": rid, "error": f"no such workflow: {name!r}"})
                return
            detail = _workflow_dict(w)
            detail["topology"] = w.topology() if w.topology is not None else None
            await emit({"id": rid, "result": detail})

        async def _workspaces_list(_p: dict) -> None:
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            rows = await workspaces.list()
            await emit(
                {
                    "id": rid,
                    "result": [{**r, "active": r["name"] == active_name} for r in rows],
                }
            )

        async def _workspaces_show(p: dict) -> None:
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            name = p.get("name") or active_name
            row = await workspaces.get(name)
            if row is None:
                await emit({"id": rid, "error": f"no such workspace: {name}"})
                return
            home = workspaces.home()
            await emit(
                {
                    "id": rid,
                    "result": {
                        **row,
                        "active": name == active_name,
                        "prompts_dir": str(workspaces.prompts_dir(name)),
                        "root": str(home.root),
                        "db_url": home.db_url,
                        "env_file": str(home.env_file),
                        "log_file": str(home.log_file),
                        "connectors_file": str(home.connectors_file),
                    },
                }
            )

        async def _workspaces_create(p: dict) -> None:
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            row = await workspaces.create(p["name"])
            await emit({"id": rid, "result": {**row, "active": False}})

        async def _workspaces_use(p: dict) -> None:
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            name = p["name"]
            if await workspaces.get(name) is None:
                await emit({"id": rid, "error": f"no such workspace: {name}"})
                return
            old = services["active_name"]
            if config is not None:
                await config.switch(name)
            try:
                rebuild = services.get("rebuild")
                if rebuild is not None:
                    fresh = rebuild(name, config=config)
                    fresh.pop("workspaces", None)  # keep the (possibly faked) instance
                    services.update(fresh)
                services["active_name"] = name
                # Marker persists only after the in-process switch succeeded — a
                # mid-switch failure must never leave the marker pointing at a
                # workspace this process never actually switched to.
                await workspaces.set_active(name)
            except Exception:
                if config is not None:
                    # ponytail: switch-back keeps config/env symmetric with
                    # services on a mid-switch failure; the marker only ever
                    # moves last, so a crash self-heals on restart.
                    await config.switch(old)
                raise
            await emit({"id": rid, "result": {"name": name, "active": True}})

        async def _workspaces_rename(p: dict) -> None:
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            name = p["name"]
            new_name = p["new_name"]
            renaming_active = name == services["active_name"]
            row = await workspaces.rename(name, new_name)
            if not renaming_active:
                await emit({"id": rid, "result": {**row, "active": False}})
                return
            # The rename already moved the marker (unlike `use`, where it moves
            # last) — a failure below leaves the rename durable, which is
            # correct: the rename itself succeeded. The client sees {id, error}
            # and re-selecting the workspace retries the switch tail.
            if config is not None:
                await config.switch(new_name)
            rebuild = services.get("rebuild")
            if rebuild is not None:
                fresh = rebuild(new_name, config=config)
                fresh.pop("workspaces", None)  # keep the (possibly faked) instance
                services.update(fresh)
            services["active_name"] = new_name
            await emit({"id": rid, "result": {**row, "active": True}})

        async def _sessions_list(_p: dict) -> None:
            rows = await sessions.list()
            await emit({"id": rid, "result": [_session_dict(s) for s in rows]})

        async def _sessions_show(p: dict) -> None:
            sid = p["session_id"]
            session = await sessions.get(sid)
            if session is None:
                await emit({"id": rid, "error": f"no such session: {sid}"})
                return
            event_list = await sessions.events(sid)
            events = [
                {"type": etype, "payload": payload}
                for etype, payload in (serialize_event(e) for e in event_list)
            ]
            await emit(
                {
                    "id": rid,
                    "result": {"session": _session_dict(session), "events": events},
                }
            )

        async def _decisions_list(_p: dict) -> None:
            if decisions is None:
                raise RuntimeError("decisions service not available")
            rows = await decisions.list()
            await emit({"id": rid, "result": [_decision_summary(d) for d in rows]})

        async def _decisions_show(p: dict) -> None:
            if decisions is None:
                raise RuntimeError("decisions service not available")
            did = p["decision_id"]
            record, outcomes = await decisions.get(did)
            if record is None:
                await emit({"id": rid, "error": f"no such decision: {did}"})
                return
            await emit({"id": rid, "result": _decision_detail(record, outcomes)})

        async def _connectors_list(_p: dict) -> None:
            if connectors is None:
                raise RuntimeError("connectors service not available")
            result = _connector_plan_dict(await connectors.plan())
            result["last_synced"] = await connectors.last_synced()
            await emit({"id": rid, "result": result})

        async def _connectors_health(p: dict) -> None:
            if connectors is None:
                raise RuntimeError("connectors service not available")
            report = await connectors.health(connector=p.get("connector"))
            await emit({"id": rid, "result": _health_dict(report)})

        async def _connectors_sync(p: dict) -> None:
            if connectors is None:
                raise RuntimeError("connectors service not available")
            report = await connectors.sync(connector=p.get("connector"))
            await emit({"id": rid, "result": _sync_dict(report)})

        async def _prompts_list(_p: dict) -> None:
            if prompts is None:
                raise RuntimeError("prompts service not available")
            summaries = [_prompt_summary(prompts, n) for n in prompts.names()]
            await emit({"id": rid, "result": summaries})

        async def _prompts_show(p: dict) -> None:
            if prompts is None:
                raise RuntimeError("prompts service not available")
            name = p["name"]
            version = p["version"]
            text = prompts.read(name, version)
            await emit(
                {"id": rid, "result": {"name": name, "version": version, "text": text}}
            )

        async def _prompts_diff(p: dict) -> None:
            if prompts is None:
                raise RuntimeError("prompts service not available")
            name = p["name"]
            old = p["old"]
            new = p["new"]
            diff = prompts.diff(name, old, new)
            await emit(
                {
                    "id": rid,
                    "result": {"name": name, "old": old, "new": new, "diff": diff},
                }
            )

        async def _prompts_save(p: dict) -> None:
            if prompts is None:
                raise RuntimeError("prompts service not available")
            name = p["name"]
            prompts.save(name, p["text"])
            await emit({"id": rid, "result": _prompt_summary(prompts, name)})

        async def _prompts_rollback(p: dict) -> None:
            if prompts is None:
                raise RuntimeError("prompts service not available")
            name = p["name"]
            prompts.rollback(name, p["version"])
            await emit({"id": rid, "result": _prompt_summary(prompts, name)})

        async def _config_get(_p: dict) -> None:
            if config is None:
                raise RuntimeError("config service not available")
            await emit({"id": rid, "result": _config_dict(config)})

        async def _reflection_record(p: dict) -> None:
            if reflection is None:
                raise RuntimeError("reflection service not available")
            did = p["decision_id"]
            note = p.get("note", "")
            try:
                outcome = await reflection.reflect_on(did, note)
            except LookupError:
                await emit({"id": rid, "error": f"no such decision: {did}"})
                return
            await emit({"id": rid, "result": outcome.model_dump(mode="json")})

        async def _config_set(p: dict) -> None:
            if config is None:
                raise RuntimeError("config service not available")
            await config.set(
                p["model"],
                provider=p.get("provider"),
                api_key=p.get("api_key"),
                settings=p.get("settings"),
            )
            await emit({"id": rid, "result": _config_dict(config)})

        async def _preferences_get(_p: dict) -> None:
            if preferences is None:
                raise RuntimeError("preferences service not available")
            prefs = await preferences.all()
            await emit({"id": rid, "result": {"theme": prefs.get("theme")}})

        async def _preferences_set(p: dict) -> None:
            if preferences is None:
                raise RuntimeError("preferences service not available")
            prefs = await preferences.set("theme", p["theme"])
            await emit({"id": rid, "result": {"theme": prefs.get("theme")}})

        async def _connectors_config_list(_p: dict) -> None:
            if connectors is None:
                raise RuntimeError("connectors service not available")
            await emit({"id": rid, "result": await connectors.config_list()})

        async def _connectors_config_save(p: dict) -> None:
            if connectors is None:
                raise RuntimeError("connectors service not available")
            entry = await connectors.config_save(
                p["connector"], p.get("config") or {}, secrets=p.get("secrets")
            )
            await emit({"id": rid, "result": entry})

        async def _memory_lessons(_p: dict) -> None:
            if memory is None:
                raise RuntimeError("memory service not available")
            rows = await memory.lessons()
            await emit({"id": rid, "result": [_lesson_dict(x) for x in rows]})

        async def _run_cancel(p: dict) -> None:
            ok = workflows.cancel(p.get("session_id", ""))
            await emit({"id": rid, "result": {"ok": ok}})

        table: dict[str, Callable[[dict], Awaitable[None]]] = {
            "workflows.list": _workflows_list,
            "workflows.show": _workflows_show,
            "workspaces.list": _workspaces_list,
            "workspaces.show": _workspaces_show,
            "workspaces.create": _workspaces_create,
            "workspaces.use": _workspaces_use,
            "workspaces.rename": _workspaces_rename,
            "sessions.list": _sessions_list,
            "sessions.show": _sessions_show,
            "decisions.list": _decisions_list,
            "decisions.show": _decisions_show,
            "connectors.list": _connectors_list,
            "connectors.health": _connectors_health,
            "connectors.sync": _connectors_sync,
            "prompts.list": _prompts_list,
            "prompts.show": _prompts_show,
            "prompts.diff": _prompts_diff,
            "prompts.save": _prompts_save,
            "prompts.rollback": _prompts_rollback,
            "config.get": _config_get,
            "config.set": _config_set,
            "preferences.get": _preferences_get,
            "preferences.set": _preferences_set,
            "connectors.config.list": _connectors_config_list,
            "connectors.config.save": _connectors_config_save,
            "reflection.record": _reflection_record,
            "memory.lessons": _memory_lessons,
            "run.cancel": _run_cancel,
        }

        handler = table.get(method)
        if handler is None:
            await emit({"id": rid, "error": f"unknown method: {method!r}"})
            return
        await handler(params)

    except Exception as exc:  # noqa: BLE001 — one bad request must not kill the loop
        await emit({"id": rid, "error": f"{type(exc).__name__}: {exc}"})


async def serve(
    services: dict,
    *,
    read_line: Callable[[], Awaitable[str]] | None = None,
    write_line: Callable[[str], None] | None = None,
) -> None:
    """Read NDJSON requests, dispatch each, write NDJSON responses, until EOF.

    Sequential: one request is fully serviced (a run fully streamed) before the
    next line is read. ponytail: single in-flight request, no concurrency — add a
    task-per-request dispatcher only when the GUI needs to call mid-run.
    """
    if read_line is None:
        loop = asyncio.get_running_loop()
        _lines: asyncio.Queue[str] = asyncio.Queue()

        async def _pump() -> None:
            while True:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                await _lines.put(line)
                if not line:  # EOF
                    return

        pump_task = asyncio.ensure_future(_pump())  # noqa: F841, RUF006 — keepalive; task runs for the serve-loop lifetime

        async def read_line() -> str:
            return await _lines.get()

    if write_line is None:

        def write_line(line: str) -> None:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()

    async def emit(message: dict) -> None:
        write_line(json.dumps(message))

    while True:
        raw = await read_line()
        if not raw:  # EOF
            return
        raw = raw.strip()
        if not raw:
            continue
        try:
            request = json.loads(raw)
        except json.JSONDecodeError as exc:
            await emit({"id": None, "error": f"invalid json: {exc}"})
            continue
        await handle(request, services, read_line=read_line, emit=emit)
