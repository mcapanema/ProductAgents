# app/ — presentation adapters

`productagents.app` is the presentation layer. It is a **thin client of the
`productagents.platform` Application Services**: it imports only `platform.*`,
`core.*`, and sibling `app.*` modules — never `agents`, `memory`, `knowledge`,
or `connectors`.

## Adapters

| Module | Role |
| --- | --- |
| `cli.py` | The command-line client and the `productagents` console entry point (`main`). Parses args with stdlib `argparse` and dispatches to platform services. No subcommand → `launch_tui`. Subcommands: `run`, `sync`, `workspace list/show`, `sessions list/show`, `prompts list/show/diff/save/rollback`. |
| `tui/` | The Textual GUI (see `tui/CLAUDE.md`). `launch_tui(workspace_name)` builds and runs the app; `_build_app` is the composition root. |
| `ipc.py` | JSON-over-stdio client for out-of-process GUIs (Phase 8 Tauri sidecar). `productagents ipc` serves newline-delimited JSON: one request per stdin line → one or more response lines, each echoing the request `id`. Methods mirror the CLI surface (`workflows.list`, `workspaces.list/show`, `sessions.list/show`, `decisions.list/show`, `connectors.list/health/sync`, `prompts.list/show/diff`, `run`). `run` streams `{event:{type,payload}}` lines then a terminal `{result:{status,session_id}}`. Imports only platform/core/sibling-app, same contract as `cli.py`. |
| `devbridge.py` | **Dev-only** WebSocket bridge over the *same* Application Layer as `ipc.py`. `productagents serve-ws [--port 7420]` serves `ipc.handle` to a browser at `ws://127.0.0.1:<port>` so the React frontend (Vite dev server, outside the Tauri shell) and Playwright can exercise the full UI with live data. Reuses `ipc.handle` + `ipc.build_services` verbatim — only the transport (one WS text message per request line) differs. Localhost-bound; never bundled into the shipped app. |
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
- `workspace`/`sessions`/`prompts` with no sub-action default to `list`.
- `prompts list` lists all prompt names with their active version (`(v0)` = bundled
  default). `prompts show NAME [--version N]` prints the template text. `prompts diff
  NAME` shows a unified diff between the bundled default and the workspace-active
  version. `prompts save NAME FILE` appends a new version from `FILE`. `prompts
  rollback NAME` removes the latest workspace version (falls back to the previous
  override, or the bundled default). All `prompts` handlers take `service: PromptService`
  by keyword for offline testing.

## IPC protocol (Phase 6)

`ipc.serve(...)` is the stdin→`handle`→stdout loop; `ipc.handle(request, *, …, emit)`
dispatches one request. Both take their collaborating services by keyword so they
test offline (`tests/test_ipc.py`) — no real model, no real stdin/stdout. Envelope:
request `{id, method, params?}`; responses `{id, event:{type,payload}}` (run only),
`{id, result}`, or `{id, error}`. Events reuse `platform.serialization.serialize_event`,
so a new platform event needs no IPC change. The loop is sequential and degrades on
bad input — only EOF ends it.

The `error` values in `{id, error}` responses are human-facing strings (not a machine-parseable taxonomy); a Phase 8 GUI should match on the envelope shape (`event`/`result`/`error` keys), not parse error text.

Deferred (YAGNI): human-in-the-loop approval over the wire (the seam is a
server→client `approval_request` message + a client `approve` method; headless
`run` is `human_in_the_loop=False`); concurrent in-flight requests.

A **dev-only** WebSocket transport now exists in `devbridge.py` (`productagents
serve-ws`) for browser/Playwright UI testing — it reuses `ipc.handle` +
`ipc.build_services`, so a new method/event needs no bridge change. It is a
localhost dev affordance, not the product client/server split (which remains
deferred); the shipped Tauri app still talks NDJSON over stdio.

`decisions.list` → `[{id, title, recommendation, confidence, created_at}]` (summaries
from the DecisionStore via `DecisionReadService`). `decisions.show {decision_id}` →
`{record: <full DecisionRecord dump>, outcomes: [<OutcomeRecord dump>...]}`; `error`
"no such decision: <id>" if unknown. These read the decision system-of-record (org
memory), distinct from `sessions.*` which replays the execution event log.

`connectors.list` → `{connectors: [{name}], problems: [str]}` — the static, no-I/O
config view from `ConnectorService.plan()` (names only; resolved secrets never leave
the platform). `connectors.health` → `{statuses: {name: {ok, detail}}, problems}` probes
each enabled connector's readiness. `connectors.sync` → `{results: [{connector, written,
ok, error}], problems}` runs one sync pass. All three are guarded by a `connectors=None`
kwarg (mirrors `decisions`) and emit a human-facing `error` if the service is absent.

`prompts.list` → `[{name, versions: [int], active: int}]` — every prompt name with its
version list (`0` = bundled default) and active (highest) version, from `PromptService`.
`prompts.show {name, version}` → `{name, version, text}` reads one version's template.
`prompts.diff {name, old, new}` → `{name, old, new, diff}` returns the unified diff between
two versions. All three are read-only and guarded by a `prompts=None` kwarg (mirrors
`connectors`), emitting a human-facing `error` if the service is absent. GUI prompt
*editing* (save/rollback) is deferred; the `prompts` CLI still owns the write surface.
