"""Dev-only WebSocket bridge over the same Application Layer as ``ipc``.

Exposes ``ipc.handle`` to a browser at ``ws://127.0.0.1:<port>`` so the React
frontend served by ``vite`` at ``localhost:1420`` (i.e. outside the Tauri shell)
— and Playwright driving it — can exercise the full UI with live data. The native
Tauri app does NOT use this; it talks NDJSON over stdio (``productagents ipc``).

This is a **development affordance**: it binds to localhost only and is never
bundled into the shipped desktop app. It does not introduce a client/server
product surface — it is the same local-first Application Layer, reached over a
local socket instead of stdio so a browser-based test harness can attach.

ponytail: reuses ``ipc.handle`` verbatim — only the framing differs (one WS text
message per request line instead of one stdin line). No dispatch logic, no
service wiring is duplicated; ``websockets`` is already in the resolved env.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

import websockets

from productagents.app import ipc

DEFAULT_PORT = 7420


async def _handle_connection(websocket, *, services: dict) -> None:
    """Serve one browser connection: each text message is one request line.

    Mirrors ``ipc.serve``'s loop but over a WebSocket — dispatch goes through the
    shared ``ipc.handle`` so the degrade-never-crash contract and the full method
    surface (``workflows``/``workspaces``/``sessions``/``decisions``/``run``) are
    identical to the stdio transport. A malformed message becomes one ``error``
    response; the connection survives until the client disconnects.
    """

    async def emit(message: dict) -> None:
        await websocket.send(json.dumps(message))

    async def read_line() -> str:
        # HITL: the approver reads the client's next message while the run is
        # paused inside handle(). The `async for` below is suspended at the
        # `await ipc.handle(...)` line, so this recv() takes the next frame.
        return await websocket.recv()

    try:
        async for raw in websocket:
            text = raw.strip() if isinstance(raw, str) else raw
            if not text:
                continue
            try:
                request = json.loads(text)
            except (json.JSONDecodeError, TypeError) as exc:
                await emit({"id": None, "error": f"invalid json: {exc}"})
                continue
            await ipc.handle(request, services, emit=emit, read_line=read_line)
    except websockets.exceptions.ConnectionClosed:
        return  # client went away mid-request; nothing to clean up


async def _serve(active_name: str, *, port: int, config=None) -> None:
    # ponytail: a TCP port-readiness probe (e.g. Playwright's webServer check)
    # opens a non-WebSocket connection that websockets logs as a failed
    # handshake. Quiet that probe noise; a real client that can't connect still
    # surfaces as a dropped connection the browser handles.
    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)
    services = ipc.build_services(active_name, config=config)
    async with websockets.serve(
        lambda ws: _handle_connection(ws, services=services),
        "127.0.0.1",
        port,
    ):
        await asyncio.Future()  # run until cancelled / interrupted


def serve_ws(active_name: str, *, port: int = DEFAULT_PORT, config=None) -> None:
    """Run the dev WebSocket bridge on ``127.0.0.1:<port>`` until interrupted.

    Backs ``productagents serve-ws``. Ctrl+C exits cleanly.
    """
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_serve(active_name, port=port, config=config))
