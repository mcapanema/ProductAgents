"""JSON-over-stdio IPC client of the ProductAgents Application Layer.

A presentation adapter for out-of-process clients (the future Tauri GUI). It
speaks newline-delimited JSON on stdin/stdout: one request object per input
line, one or more response objects per output line, each echoing the request
``id``. Like ``cli.py`` it imports only ``platform`` + ``core`` + sibling
``app`` modules and drives the same Application Services — proving the
Application Layer is sufficient to run the platform across a process boundary.

ponytail: NDJSON over stdio, not HTTP. The vision is local-first with no remote
APIs (v3-concepts.md), and Tauri launches the Python backend as a child process
it talks to over stdio. The product client/server split stays deferred; the only
non-stdio transport is ``devbridge.py``, a dev-only localhost WebSocket that
reuses ``handle`` + ``build_services`` for browser/Playwright UI testing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from productagents.app import setup
from productagents.core.models import HumanDecision, Initiative
from productagents.platform import events as ev
from productagents.platform.connector_service import ConnectorService
from productagents.platform.decision_read_service import DecisionReadService
from productagents.platform.prompt_service import PromptService
from productagents.platform.serialization import serialize_event
from productagents.platform.session import Session
from productagents.platform.session_service import SessionService
from productagents.platform.workflow import Workflow, WorkflowService
from productagents.platform.workspace import Workspace, WorkspaceService

logger = logging.getLogger(__name__)

Emit = Callable[[dict], Awaitable[None]]


def _build_workflows(*, human_in_the_loop: bool) -> WorkflowService:
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
        return _build_run_service(human_in_the_loop=human_in_the_loop)
    except Exception:  # noqa: BLE001 — degraded mode; any failure (missing key, bad config) must not crash the sidecar
        logger.warning(
            "model unavailable; runs disabled until an API key is set", exc_info=True
        )
        return WorkflowService.for_model(
            None, recorder=make_recorder(), human_in_the_loop=human_in_the_loop
        )


def _build_reflection():
    """ReflectionService for the GUI, or None if no model is available yet."""
    from productagents.platform.llm import get_model
    from productagents.platform.reflection_service import ReflectionService

    try:
        return ReflectionService.for_model(get_model())
    except Exception:  # noqa: BLE001
        logger.warning(
            "model unavailable; reflection disabled until an API key is set",
            exc_info=True,
        )
        return None


def build_services(active_name: str) -> dict:
    """Construct the production Application Services the IPC adapters dispatch to.

    Shared by ``serve_stdio`` (stdio transport) and the dev WebSocket bridge
    (``devbridge.py``) so both expose the identical surface. Builds a real
    model-backed WorkflowService (so ``run`` works), plus the workspace + session
    + decision read services. The returned dict is exactly the keyword set
    ``serve`` / ``handle`` consume.

    ponytail: the model is built up front, so even read methods need a key. Make
    the WorkflowService lazy-on-first-run only if a client must browse without one.
    """
    return {
        "workflows": _build_workflows(human_in_the_loop=True),
        "workspaces": WorkspaceService(),
        "active_name": active_name,
        "sessions": SessionService.create(),
        "decisions": DecisionReadService.create(),
        "connectors": ConnectorService(),
        "prompts": PromptService.create(),
        "config": setup,
        "reflection": _build_reflection(),
    }


def serve_stdio(active_name: str) -> None:
    """Build production services and serve the stdio loop until EOF.

    Backs ``productagents ipc``. The Tauri shell (Phase 8) spawns this as its
    sidecar.
    """
    asyncio.run(serve(**build_services(active_name)))


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
    failed = False
    async for event in stream:
        if isinstance(event, ev.SessionFailed):
            failed = True
        etype, payload = serialize_event(event)
        await emit({"id": rid, "event": {"type": etype, "payload": payload}})
    await emit(
        {
            "id": rid,
            "result": {
                "status": "failed" if failed else "finished",
                "session_id": session.id,
            },
        }
    )


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


def _workflow_dict(w: Workflow) -> dict:
    return {"name": w.name, "title": w.title, "description": w.description}


def _workspace_dict(ws: Workspace, *, active_name: str) -> dict:
    return {
        "name": ws.name,
        "active": ws.name == active_name,
        "root": str(ws.root),
        "db_url": ws.db_url,
        "connectors_file": str(ws.connectors_file),
        "env_file": str(ws.env_file),
        "log_file": str(ws.log_file),
    }


def _session_dict(s: Session) -> dict:
    return {
        "id": s.id,
        "workflow": s.workflow,
        "status": s.status,
        "created_at": s.created_at.isoformat(),
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
    status = config.check_config()
    return {
        "model": status.model,
        "provider": status.provider,
        "key_var": status.key_var,
        "key_present": status.key_present,
        "problems": status.problems,
        "providers": [
            {
                "id": pid,
                "label": info.label,
                "key_var": info.key_var,
                "default_model": info.default_model,
            }
            for pid, info in config.PROVIDERS.items()
        ],
    }


async def handle(
    request: dict,
    *,
    workflows: WorkflowService,
    workspaces: WorkspaceService | None,
    active_name: str,
    sessions,
    decisions: Any = None,
    connectors: Any = None,
    prompts: Any = None,
    config: Any = None,
    reflection: Any = None,
    read_line: Callable[[], Awaitable[str]] | None = None,
    emit: Emit,
) -> None:
    """Dispatch one request, emitting one or more response messages.

    Every emitted message echoes ``request['id']``. Every method except ``run``
    emits a single ``result``; any failure becomes one ``error`` message so the
    serve loop never dies on a single bad request.
    """
    rid = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}
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

        async def _workspaces_list(_p: dict) -> None:
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            wss = [
                _workspace_dict(ws, active_name=active_name) for ws in workspaces.list()
            ]
            await emit({"id": rid, "result": wss})

        async def _workspaces_show(p: dict) -> None:
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            ws = workspaces.resolve(p.get("name"))
            ws_dict = _workspace_dict(ws, active_name=active_name)
            await emit({"id": rid, "result": ws_dict})

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
            await emit({"id": rid, "result": _connector_plan_dict(connectors.plan())})

        async def _connectors_health(_p: dict) -> None:
            if connectors is None:
                raise RuntimeError("connectors service not available")
            report = await connectors.health()
            await emit({"id": rid, "result": _health_dict(report)})

        async def _connectors_sync(_p: dict) -> None:
            if connectors is None:
                raise RuntimeError("connectors service not available")
            report = await connectors.sync()
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
            model = p["model"]
            provider = p.get("provider")
            values = {"PRODUCTAGENTS_MODEL": model}
            if provider:
                values["PRODUCTAGENTS_MODEL_PROVIDER"] = provider
            api_key = p.get("api_key")
            if api_key:  # never write a blank key over an existing one
                key_var = config.api_key_var_for(provider or config.provider_for(model))
                if key_var:
                    values[key_var] = api_key
            dotenv_path = None
            if workspaces is not None:
                dotenv_path = str(workspaces.resolve(active_name).env_file)
            config.write_env(values, dotenv_path=dotenv_path)
            await emit({"id": rid, "result": _config_dict(config)})

        table: dict[str, Callable[[dict], Awaitable[None]]] = {
            "workflows.list": _workflows_list,
            "workspaces.list": _workspaces_list,
            "workspaces.show": _workspaces_show,
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
            "reflection.record": _reflection_record,
        }

        handler = table.get(method)
        if handler is None:
            await emit({"id": rid, "error": f"unknown method: {method!r}"})
            return
        await handler(params)

    except Exception as exc:  # noqa: BLE001 — one bad request must not kill the loop
        await emit({"id": rid, "error": f"{type(exc).__name__}: {exc}"})


async def serve(
    *,
    workflows: WorkflowService,
    workspaces: WorkspaceService | None,
    active_name: str,
    sessions,
    decisions: Any = None,
    connectors: Any = None,
    prompts: Any = None,
    config: Any = None,
    reflection: Any = None,
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

        async def read_line() -> str:
            return await loop.run_in_executor(None, sys.stdin.readline)

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
        await handle(
            request,
            workflows=workflows,
            workspaces=workspaces,
            active_name=active_name,
            sessions=sessions,
            decisions=decisions,
            connectors=connectors,
            prompts=prompts,
            config=config,
            reflection=reflection,
            read_line=read_line,
            emit=emit,
        )
