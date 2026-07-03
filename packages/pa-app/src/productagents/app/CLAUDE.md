# app/ — presentation adapters

`productagents.app` is the presentation layer. It is a **thin client of the
`productagents.platform` Application Services**: it imports only `platform.*`,
`core.*`, and sibling `app.*` modules — never `agents`, `memory`, `knowledge`,
or `connectors`.

## Adapters

| Module | Role |
| --- | --- |
| `cli.py` | The command-line client and the `productagents` console entry point (`main`). Parses args with stdlib `argparse` and dispatches to platform services. No subcommand → prints help. Subcommands: `run`, `sync`, `workspace list/show/create/use`, `sessions list/show`, `decisions export`, `prompts list/show/diff/save/rollback`, `reflect`. |
| `ipc.py` | JSON-over-stdio client for out-of-process GUIs (Phase 8 Tauri sidecar). `productagents ipc` serves newline-delimited JSON: one request per stdin line → one or more response lines, each echoing the request `id`. Methods mirror the CLI surface (`workflows.list/show`, `workspaces.list/show/create/use`, `sessions.list/show`, `decisions.list/show`, `connectors.list/health/sync`, `prompts.list/show/diff/save/rollback`, `config.get/set`, `run`). `run` streams `{event:{type,payload}}` lines then a terminal `{result:{status,session_id}}`. Imports only platform/core/sibling-app, same contract as `cli.py`. |
| `devbridge.py` | **Dev-only** WebSocket bridge over the *same* Application Layer as `ipc.py`. `productagents serve-ws [--port 7420]` serves `ipc.handle` to a browser at `ws://127.0.0.1:<port>` so the React frontend (Vite dev server, outside the Tauri shell) and Playwright can exercise the full UI with live data. Reuses `ipc.handle` + `ipc.build_services` verbatim — only the transport (one WS text message per request line) differs. Localhost-bound; never bundled into the shipped app. |

## CLI contract

`main(argv=None)` always: `WorkspaceService().activate()` (point env vars at the
shared home, `PRODUCTAGENTS_HOME`) → `load_env()` → resolve the active workspace
name (`workspaces.resolve(--workspace)`: flag > `PRODUCTAGENTS_WORKSPACE` env >
the persisted `.active` marker > `default`) → `bootstrap_home()` (idempotent:
legacy adoption + `create_all` schema, see root CLAUDE.md) → `ConfigurationService.load()`
(workspace-DB tunables → env) → `configure_logging()` → dispatch. Every command handler
returns an `int` exit code; `main` raises `SystemExit(code)`. Handlers take their
collaborating service via a keyword arg so they test headless (see
`tests/test_cli.py`) — no command builds a real model or hits the network in tests.

- `run WORKFLOW TITLE [--evidence SPEC]` builds a real `WorkflowService`
  (`human_in_the_loop=False`) and streams events through `render_event`. Exit 1
  on a `SessionFailed`.
- `render_event(event)` is the CLI's per-event text renderer — one line per event, `None` to skip.
- `workspace`/`sessions`/`prompts` with no sub-action default to `list`.
- `prompts list` lists all prompt names with their active version (`(v0)` = bundled
  default). `prompts show NAME [--version N]` prints the template text. `prompts diff
  NAME` shows a unified diff between the bundled default and the workspace-active
  version. `prompts save NAME FILE` appends a new version from `FILE`. `prompts
  rollback NAME` removes the latest workspace version (falls back to the previous
  override, or the bundled default). All `prompts` handlers take `service: PromptService`
  by keyword for offline testing.
- `reflect` with no args lists past decisions (id + title + created_at) from the decision
  store, formatted for selection. `reflect DECISION_ID NOTE` runs the reflection agent
  (`platform.reflect`) against the named decision and persists the `OutcomeRecord`.
  Handlers take `service: ReflectionService` by keyword for offline testing.

## IPC protocol (Phase 6)

`ipc.serve(...)` is the stdin→`handle`→stdout loop; `ipc.handle(request, *, …, emit)`
dispatches one request. Both take their collaborating services by keyword so they
test offline (`tests/test_ipc.py`) — no real model, no real stdin/stdout. Envelope:
request `{id, method, params?}`; responses `{id, event:{type,payload}}` (run only),
`{id, result}`, or `{id, error}`. Events reuse `platform.serialization.serialize_event`,
so a new platform event needs no IPC change. The loop is sequential and degrades on
bad input — only EOF ends it.

The `error` values in `{id, error}` responses are human-facing strings (not a machine-parseable taxonomy); a Phase 8 GUI should match on the envelope shape (`event`/`result`/`error` keys), not parse error text.

Human-in-the-loop approval now works over the wire. `run {…, approval: true}`
builds a HITL workflow service; when the graph pauses at governance the platform
streams an `ApprovalRequested` event and the run's approver reads the client's
**next** request line as the decision: `approve {verdict, rationale?}` (verdict ∈
`approve`/`reject`/`request_analysis`, invalid → `approve`). The server acks the
approve message `{id, result: {ok: true}}` and resumes; a `FinalVerdict` event
follows. The serve loop is sequential, so the approver simply reads the next line
— no concurrency, single in-flight request (the client must not send other
requests while a run awaits approval). `approval` defaults false (headless run).
Still deferred: concurrent in-flight requests.

A **dev-only** WebSocket transport now exists in `devbridge.py` (`productagents
serve-ws`) for browser/Playwright UI testing — it reuses `ipc.handle` +
`ipc.build_services`, so a new method/event needs no bridge change. It is a
localhost dev affordance, not the product client/server split (which remains
deferred); the shipped Tauri app still talks NDJSON over stdio.

`workflows.show {name}` → `{name, title, description, topology}` — one registered
workflow plus its graph structure: `topology` is `{nodes: [{id, prompts: [str]}],
edges: [{source, target, conditional}]}` from the workflow's registered topology
accessor (`Workflow.topology`), or `null` when the workflow does not expose one.
`prompts` lists the prompt-registry names the node renders (so the GUI can wire
node-click → the existing `prompts.*` surface). `error` "no such workflow: <name>"
if unknown.

`decisions.list` → `[{id, title, recommendation, confidence, created_at}]` (summaries
from the DecisionStore via `DecisionReadService`). `decisions.show {decision_id}` →
`{record: <full DecisionRecord dump>, outcomes: [<OutcomeRecord dump>...]}`; `error`
"no such decision: <id>" if unknown. These read the decision system-of-record (org
memory), distinct from `sessions.*` which replays the execution event log.

`connectors.list` → `{connectors: [{name}], problems: [str], last_synced: {name: iso}}` — the
static, no-I/O config view from `ConnectorService.plan()` plus a cheap `last_synced` map
(connector key → ISO-8601 timestamp of last successful cursor write, from `SyncStateStore`;
empty if the connector has never synced). Resolved secrets never leave the platform. `connectors.health {connector?}` → `{statuses: {name: {ok, detail}}, problems}` probes
each enabled connector's readiness — or just the named one when `connector` is given.
`connectors.sync {connector?}` → `{results: [{connector, written,
ok, error}], problems}` runs one sync pass, scoped the same way. An unknown/unconfigured
`connector` degrades to an empty report with a `"connector '<name>': not configured"`
problem (a `result`, not an `error`). All three are guarded by a `connectors=None`
kwarg (mirrors `decisions`) and emit a human-facing `error` if the service is absent.

`prompts.list` → `[{name, versions: [int], active: int}]` — every prompt name with its
version list (`0` = bundled default) and active (highest) version, from `PromptService`.
`prompts.show {name, version}` → `{name, version, text}` reads one version's template.
`prompts.diff {name, old, new}` → `{name, old, new, diff}` returns the unified diff between
two versions. All read methods are guarded by a `prompts=None` kwarg (mirrors
`connectors`), emitting a human-facing `error` if the service is absent.
`prompts.save {name, text}` → updated `{name, versions, active}` — appends a new version.
`prompts.rollback {name, version}` → updated `{name, versions, active}` — re-saves an old version as the new active.

`config.get` → `{model, provider, key_var, key_present, problems, settings:
{debate_rounds, judge_threshold, judge_max_retries, max_retries}, origins:
{model, model_provider, debate_rounds, judge_threshold, judge_max_retries,
max_retries: "override"|"env"|"db"|"default"}, providers: [{id, label, key_var,
default_model}]}` — the static readiness check (`ConfigurationService.status()`)
plus the current tunables (`.settings()`), which precedence tier supplies each
workspace key right now (`.settings_origins()`, so the GUI can label a field
"overridden by environment" instead of a save that mysteriously doesn't apply),
and the provider catalog (`.providers()`) for the Settings panel. `config.set
{model, provider?, api_key?, settings?}` awaits `ConfigurationService.set()`,
which writes the four tunables to the workspace DB and the model/provider/API
key to the **active workspace's** `.env` (never a blank api_key over an
existing one) — before returning the refreshed status. Logging is runtime
config (not part of this whitelist); connector config (including GitHub) owns
its own `connectors.config.*` surface below. Both are guarded by a
`config=None` kwarg. This is the GUI's settings **write** surface for the
model/provider/tunables; prompt editing stays deferred.

`preferences.get` → `{"theme": string | null}` reads workspace-DB preferences
(`PreferenceService.all()`). `preferences.set {theme}` → same shape, writes via
`PreferenceService.set("theme", ...)`. `theme` is the only whitelisted
preference key today — preferences affect the user experience, never workflow
execution, which is why they get their own store/whitelist instead of routing
through `ConfigurationService`. Guarded by a `preferences=None` kwarg; a
`ValueError` from the service (unknown key) becomes `{id, error}` like any
other handler failure.

`connectors.config.list` → `[{connector, installed, config, schema, problems}]`
— every known connector's DB-backed config block plus a JSON Schema
(`schema`) the GUI form renders from, from `ConnectorService.config_list()`.
`connectors.config.save {connector, config, secrets?}` → the updated single
entry, from `ConnectorService.config_save()`, which validates the block
against its schema before writing (a `ValueError` with a human-facing message
becomes `{id, error}`); `secrets` is a map of secret values written to the
active workspace's `.env` — only for the `*_env`-referenced variable names the
connector's schema declares, and a blank secret value is skipped rather than
overwriting a stored one. Both guarded by the existing `connectors=None`
kwarg.

Workspaces are rows in the shared home's `workspace` table, not directories —
every workspace shares one DB/`.env`/log under `PRODUCTAGENTS_HOME` (see root
CLAUDE.md); a workspace only scopes rows (the `workspace` column on the scoped
stores) and owns a per-workspace prompt-override directory. `workspaces.list`
→ `[{name, created_at, active}]`. `workspaces.show {name?}` (defaults to the
active workspace) → `{name, created_at, active, prompts_dir, root, db_url,
env_file, log_file, connectors_file}` — the workspace's own prompt-override
directory (`Workspace.prompts_dir`) plus the shared home's paths (identical
for every workspace); `error` "no such workspace: <name>" if unknown.

`workspaces.create {name}` → `{name, created_at, active: false}`; `error`
"workspace already exists: <name>" / "invalid workspace name: …" on a bad
name. `workspaces.use {name}` switches **live** — no sidecar restart: checks
the workspace exists (else `error` "no such workspace: <name>"), calls
`ConfigurationService.switch(name)` (re-materializes the db/default tiers of
the six workspace-config keys for the new workspace only — a shell export or
a CLI `--set` still outranks the switch, same precedence as startup), rebuilds
every scoped service in-process via the `services["rebuild"]` seam (literally
`build_services` again, captured in the dict so a test double is still
exercised), then persists the `.active` marker **last** — only after the
in-process switch succeeded, so a mid-switch failure never leaves the marker
pointing at a workspace this process never actually switched to. Returns
`{name, active: true}`. Both guarded by the existing `workspaces=None` kwarg.
`workspaces.rename {name, new_name}` → the renamed row with `active`; renaming
the active workspace finishes with the live-switch tail (marker already moved
by the rename itself).

`reflection.record {decision_id, note}` → the `OutcomeRecord` dump
(`{decision_id, actual_outcomes, prediction_accuracy, lessons_learned, reflected_at, failed}`);
`error` "no such decision: <id>" if unknown. Guarded by a `reflection=None` kwarg.
This is the GUI's outcome-capture write surface (desktop **Reflection** panel).

`memory.lessons` → `[{decision_id, title, text, validated, prediction_accuracy}]` — the
organizational-memory lesson corpus (newest-first, up to 50 by default). Validated lessons
come from reflected outcomes; derived lessons come from the recommendation itself. Guarded by
a `memory=None` kwarg; emits `error` "memory service not available" if the service is absent.
Backed by `MemoryService` from `productagents.platform`.

`run.cancel {session_id}` → `{ok: bool}` — cooperatively cancels an in-flight run. During
a live (non-approval) `run` call, the serve loop reads control lines concurrently via
`_watch_cancel`; a matching `run.cancel` cancels the asyncio task, which emits
`SessionCancelled` and the terminal `{status:"cancelled", session_id}`. If sent as a
standalone request (no run in flight or wrong session_id), returns `{ok: false}` via the
dispatch table. HITL runs are excluded — the approver already owns the control line.
