# productagents.platform — Application Services & composition root

The Application-Services layer: the stable, presentation-agnostic API every
adapter (CLI, IPC/GUI) depends on. It wraps the agents graph, the
organizational-memory subsystem, the knowledge storage spine, and the connector
framework behind a handful of services — `DecisionService`, `ConnectorService`,
`SessionService`, `WorkflowService`, `WorkspaceService`, `PromptService`,
`ConfigurationService`, plus the `EventBus` and the platform event vocabulary.

## What's here

**Application Services** — the objects presentation code actually calls:
- `decision_service.py` — `DecisionService`: runs `evaluate_initiative` as a
  streamed session (`start_session`), translating agents-graph/runner events
  into the platform's stable event vocabulary and recording the `DecisionRecord`.
- `connector_service.py` — `ConnectorService`: sync + health-check + config
  composition root (optional `connector` key scopes a pass to one connector).
- `session_service.py` — `SessionService`: read face of the Event Store —
  list past runtime sessions, replay one's event timeline.
- `decision_read_service.py` — `DecisionReadService`: read face of the
  `DecisionStore` — list/get a past decision plus its outcomes (complements
  `session_service`: this replays *decisions*, that replays *execution*).
- `memory_service.py` — `MemoryService`: flattens past decisions + reflected
  outcomes into cross-decision `Lesson` records for the Organizational Memory
  panel (distinct from `decision_read_service`, which replays one decision).
- `workflow.py` — `WorkflowService` + `Workflow`: a workflow is a named,
  registered pipeline; today exactly one (`evaluate_initiative`).
  `Workflow.topology` feeds the GUI's graph view; the real work stays in
  `DecisionService` — this is a thin router.
- `workspace.py` — `WorkspaceService` + `SharedHome`: a workspace is a
  logical scope (a row in the `workspace` table), not a directory. `SharedHome`
  is the one shared home (one DB, one `.env`, one log) every workspace lives in.
- `prompt_service.py` — `PromptService`: Application-Layer face of the prompt
  registry (browse/read/diff/save/rollback) over the agents' `PromptStore`.
- `preference_service.py` — `PreferenceService`: GUI preference state
  (`preferences.*` IPC, today only `theme`) — kept separate from
  `ConfigurationService` because preferences affect UX, never workflow execution.
- `reflection_service.py` — `ReflectionService`: ties the decision reader, the
  out-of-graph reflection agent, and the outcome recorder into the one seam
  both `productagents reflect` and the `reflection.record` IPC call use — the
  capture half of Outcome Learning.
- `configuration.py` — `ConfigurationService`: single owner of workspace
  config precedence (`--set` CLI > exported env > workspace DB > built-in
  default). `apply_overrides` writes the top tier; `load()` seeds `os.environ`
  from the DB via `setdefault` (never clobbers); `switch()` re-scopes to
  another workspace without disturbing already-seeded/overridden keys.
  `settings_origins()` reports which tier supplies each key. Also owns the
  static, no-network `check_config`/`write_env` provider-preflight helpers.

**Event & Session vocabulary:**
- `bus.py` — `EventBus`: in-process async pub/sub (`publish`/`subscribe`/
  `close`), one `asyncio.Queue` per subscriber.
- `events.py` — the platform's stable, workflow-agnostic event vocabulary
  (frozen dataclasses: `SessionStarted` … `SessionFinished`/`SessionFailed`,
  `NodeProgress`, `AnalystCompleted`, `DebateTurnEmitted`, `RiskAssessed`,
  `Recommended`, `Judged`, `GovernanceAdvised`, `LessonsRecalled`,
  `ApprovalRequested`, `FinalVerdict`, `NodeFailed`, `SessionCancelled`).
  Every adapter matches on these, never on LangGraph/runner types.
- `session.py` — `Session`: the value type one workflow execution is tracked
  as (`id`, `workflow`, `status`, `created_at`).
- `_event_translation.py` — `status_for`/`translate`: the pure runner-result →
  platform-`Event` mapping `decision_service` uses. No I/O, no session state.
- `serialization.py` — `serialize_event`/`deserialize_event`: the bridge
  between platform `Event`s and the primitive rows the Event Store persists,
  via pydantic `TypeAdapter` — a new event type needs no change here.

**Composition roots:**
- `connectors.py` — connector YAML/DB config loading (`plan_connectors`,
  `load_db_config`) + sync runtime wiring (relocated from `pa-app`). The only
  module that imports both the connector framework and the storage layer at once.
- `workflow_registry.py` — `discover()`: entry-point (`productagents.workflows`)
  lookup backing `WorkflowService`, mirroring `connectors/registry.py`. A
  broken plugin is logged and skipped, never fatal.
- `context.py` — the graph↔store boundary: `open_agent_context` (per-run
  `AgentContext` + DB session), `open_event_store`, `open_decision_store`,
  `get_engine`, and the `make_recorder`/`make_outcome_recorder`/
  `make_decision_reader` factories the services above bind to a workspace.
  Keeps graph nodes engine-free, the same pattern `recall` uses for the
  decision log. `get_engine` caches one async engine **per running event
  loop** (aiosqlite/asyncpg connections are loop-bound).

**Seams (thin re-exports):** `llm.py`, `evidence.py`, `reflection.py`
re-export `get_model`/`DEFAULT_MODEL`, `collect_evidence`/`load_scenario`/
`EvidenceError`, and `reflect` from `pa-agents`, purely so `pa-app` can reach
these without importing `pa-agents` directly. Add a new seam here, never let
presentation import agents.

**Bootstrap:** `bootstrap.py` — `bootstrap_home()`: one-time shared-home
activation — `create_all` over both `pa-memory` and `pa-knowledge` metadata,
then (if a legacy `<home>/workspaces/default/productagents.db` exists and the
shared DB doesn't) copies its rows in stamped `workspace="default"` and
renames the legacy DB `.imported`. ponytail: `create_all` is safe only because
the shared DB is new in this release — the first real post-release schema
change must add a programmatic Alembic upgrade here instead.

## Rules that matter

- **Layer contract, stated here once:** `pa-platform` may import from
  `pa-agents`, `pa-memory`, `pa-knowledge`, `pa-connectors`, and `pa-core`. It
  is the **sole importer of `pa-connectors`** (`connector_service.py`/
  `connectors.py` are where that import lives). `pa-app` imports only
  `pa-platform` + `pa-core` — never agents, memory, knowledge, or connectors
  directly, and never langgraph/langchain/sqlalchemy. Other CLAUDE.md files
  point here rather than restating this.
- **One-time migrations run at startup, both idempotent:**
  `ConfigurationService.load()` moves the six workspace-config keys out of the
  `.env` into the `workspace_config` table; `connectors.py::load_db_config`
  does the equivalent for `connectors.yaml` → `connector_config` (both rename
  the source file `.imported`/`.invalid` so they can never re-run or re-win).
- **The Event Store is an execution log, not the system of record.** If event
  persistence fails mid-run the write is logged and swallowed — a session can
  stay stuck at `"running"`; `DecisionStore` (via `decision_read_service`)
  remains authoritative for whether a decision actually completed.
