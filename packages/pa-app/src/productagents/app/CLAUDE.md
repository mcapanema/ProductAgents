# app/ — presentation adapters

`productagents.app` is the presentation layer. It is a **thin client of the
`productagents.platform` Application Services**: it imports only `platform.*`,
`core.*`, and sibling `app.*` modules — never `agents`, `memory`, `knowledge`,
or `connectors`.

## Adapters

| Module | Role |
| --- | --- |
| `cli.py` | The command-line client and the `productagents` console entry point (`main`). Parses args with stdlib `argparse` and dispatches to platform services. No subcommand → `launch_tui`. Subcommands: `run`, `sync`, `workspace list/show`, `sessions list/show`. |
| `tui/` | The Textual GUI (see `tui/CLAUDE.md`). `launch_tui(workspace_name)` builds and runs the app; `_build_app` is the composition root. |
| `ipc.py` | JSON-over-stdio client for out-of-process GUIs (Phase 8 Tauri sidecar). `productagents ipc` serves newline-delimited JSON: one request per stdin line → one or more response lines, each echoing the request `id`. Methods mirror the CLI surface (`workflows.list`, `workspaces.list/show`, `sessions.list/show`, `run`). `run` streams `{event:{type,payload}}` lines then a terminal `{result:{status,session_id}}`. Imports only platform/core/sibling-app, same contract as `cli.py`. |
| `setup.py` | `check_config` / `write_env` readiness + `.env` writer, shared by both adapters. |

## CLI contract

`main(argv=None)` always: resolve workspace (`WorkspaceService().resolve(--workspace)`)
→ `activate` → `load_env` → `configure_logging` → dispatch. Every command handler
returns an `int` exit code; `main` raises `SystemExit(code)`. Handlers take their
collaborating service via a keyword arg so they test headless (see
`tests/test_cli.py`) — no command builds a real model or hits the network in tests.

- `run WORKFLOW TITLE [--evidence SPEC]` builds a real `WorkflowService`
  (`human_in_the_loop=False`) and streams events through `render_event`. Exit 1
  on a `SessionFailed`.
- `render_event(event)` is the pure text mirror of the TUI's per-event panel
  routing — one line per event, `None` to skip.
- `workspace`/`sessions` with no sub-action default to `list`.

## IPC protocol (Phase 6)

`ipc.serve(...)` is the stdin→`handle`→stdout loop; `ipc.handle(request, *, …, emit)`
dispatches one request. Both take their collaborating services by keyword so they
test offline (`tests/test_ipc.py`) — no real model, no real stdin/stdout. Envelope:
request `{id, method, params?}`; responses `{id, event:{type,payload}}` (run only),
`{id, result}`, or `{id, error}`. Events reuse `platform.serialization.serialize_event`,
so a new platform event needs no IPC change. The loop is sequential and degrades on
bad input — only EOF ends it.

Deferred (YAGNI): human-in-the-loop approval over the wire (the seam is a
server→client `approval_request` message + a client `approve` method; headless
`run` is `human_in_the_loop=False`); concurrent in-flight requests; an HTTP/WebSocket
transport (add only at a real client/server split).
