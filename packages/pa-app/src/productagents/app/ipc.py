"""JSON-over-stdio IPC client of the ProductAgents Application Layer.

A presentation adapter for out-of-process clients (the future Tauri GUI). It
speaks newline-delimited JSON on stdin/stdout: one request object per input
line, one or more response objects per output line, each echoing the request
``id``. Like ``cli.py`` it imports only ``platform`` + ``core`` + sibling
``app`` modules and drives the same Application Services — proving the
Application Layer is sufficient to run the platform across a process boundary.

ponytail: NDJSON over stdio, not HTTP. The vision is local-first with no remote
APIs (v3-concepts.md), and Tauri launches the Python backend as a child process
it talks to over stdio. Add an HTTP/WebSocket transport only if a real
client/server split ever arrives.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from productagents.core.models import Initiative
from productagents.platform import events as ev
from productagents.platform.serialization import serialize_event
from productagents.platform.session import Session
from productagents.platform.workflow import Workflow, WorkflowService
from productagents.platform.workspace import Workspace, WorkspaceService

Emit = Callable[[dict], Awaitable[None]]


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


async def handle(
    request: dict,
    *,
    workflows: WorkflowService,
    workspaces: WorkspaceService | None,
    active_name: str,
    sessions,
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
        elif method == "run":
            await _run(rid, params, workflows=workflows, emit=emit)
        else:
            await emit({"id": rid, "error": f"unknown method: {method!r}"})
    except Exception as exc:  # noqa: BLE001 — one bad request must not kill the loop
        await emit({"id": rid, "error": f"{type(exc).__name__}: {exc}"})
