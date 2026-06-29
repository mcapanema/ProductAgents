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
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from productagents.core.models import Initiative
from productagents.platform import events as ev
from productagents.platform.connector_service import ConnectorService
from productagents.platform.decision_read_service import DecisionReadService
from productagents.platform.serialization import serialize_event
from productagents.platform.session import Session
from productagents.platform.session_service import SessionService
from productagents.platform.workflow import Workflow, WorkflowService
from productagents.platform.workspace import Workspace, WorkspaceService

Emit = Callable[[dict], Awaitable[None]]


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
    from productagents.app.cli import _build_run_service  # reuse model wiring

    return {
        "workflows": _build_run_service(),
        "workspaces": WorkspaceService(),
        "active_name": active_name,
        "sessions": SessionService.create(),
        "decisions": DecisionReadService.create(),
        "connectors": ConnectorService(),
    }


def serve_stdio(active_name: str) -> None:
    """Build production services and serve the stdio loop until EOF.

    Backs ``productagents ipc``. The Tauri shell (Phase 8) spawns this as its
    sidecar.
    """
    asyncio.run(serve(**build_services(active_name)))


async def _run(rid, params: dict, *, workflows: WorkflowService, emit: Emit) -> None:
    """Run a workflow and stream its events, then a terminal status result.

    Mirrors the CLI's headless ``run``: governance stays advisory (no
    human-in-the-loop over the wire — see deferred items). A ``SessionFailed``
    event flips the terminal status to ``"failed"``.
    """
    title = params["title"]
    initiative = Initiative(title=title, description=title)
    session, stream = workflows.run(
        params["workflow"], initiative, params.get("evidence", "")
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


async def handle(
    request: dict,
    *,
    workflows: WorkflowService,
    workspaces: WorkspaceService | None,
    active_name: str,
    sessions,
    decisions: Any = None,
    connectors: Any = None,
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
        if method == "workflows.list":
            wfs = [_workflow_dict(w) for w in workflows.list()]
            await emit({"id": rid, "result": wfs})
        elif method == "workspaces.list":
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            wss = [
                _workspace_dict(ws, active_name=active_name) for ws in workspaces.list()
            ]
            await emit({"id": rid, "result": wss})
        elif method == "workspaces.show":
            if workspaces is None:
                raise RuntimeError("workspaces service not available")
            ws = workspaces.resolve(params.get("name"))
            ws_dict = _workspace_dict(ws, active_name=active_name)
            await emit({"id": rid, "result": ws_dict})
        elif method == "sessions.list":
            rows = await sessions.list()
            await emit({"id": rid, "result": [_session_dict(s) for s in rows]})
        elif method == "sessions.show":
            sid = params["session_id"]
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
                    "result": {
                        "session": _session_dict(session),
                        "events": events,
                    },
                }
            )
        elif method == "decisions.list":
            if decisions is None:
                raise RuntimeError("decisions service not available")
            rows = await decisions.list()
            await emit({"id": rid, "result": [_decision_summary(d) for d in rows]})
        elif method == "decisions.show":
            if decisions is None:
                raise RuntimeError("decisions service not available")
            did = params["decision_id"]
            record, outcomes = await decisions.get(did)
            if record is None:
                await emit({"id": rid, "error": f"no such decision: {did}"})
                return
            await emit({"id": rid, "result": _decision_detail(record, outcomes)})
        elif method == "connectors.list":
            if connectors is None:
                raise RuntimeError("connectors service not available")
            await emit({"id": rid, "result": _connector_plan_dict(connectors.plan())})
        elif method == "connectors.health":
            if connectors is None:
                raise RuntimeError("connectors service not available")
            report = await connectors.health()
            await emit({"id": rid, "result": _health_dict(report)})
        elif method == "connectors.sync":
            if connectors is None:
                raise RuntimeError("connectors service not available")
            report = await connectors.sync()
            await emit({"id": rid, "result": _sync_dict(report)})
        elif method == "run":
            await _run(rid, params, workflows=workflows, emit=emit)
        else:
            await emit({"id": rid, "error": f"unknown method: {method!r}"})
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
            emit=emit,
        )
