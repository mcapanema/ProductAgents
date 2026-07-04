# productagents.memory — organizational memory subsystem

Two halves the v1 code already names: **injection** (read lessons into a
decision) and **capture** (record outcomes after the fact). DB-backed since
Phase 6; JSONL demoted to export/audit.

## Layout
- `__init__.py` — re-exports ONLY the lightweight pure API (`jsonl` +
  `select_relevant_lessons`). **Never** re-export `service`/`store`/`tables`/
  `embedding`/`event_store`: that would pull SQLAlchemy into `import productagents.memory` and
  break the agents→storage import contract. Import those from their submodules.
- `jsonl.py` — append-only `decisions.jsonl`/`outcomes.jsonl` (export/audit).
- `retrieval.py` — lexical ranker (`select_relevant_lessons`, validated-first /
  derived-second + dedup) plus `cosine`/`semantic_matches`. The `also_relevant`
  set lets zero-lexical-overlap decisions in via the semantic path.
- `embedding.py` — `Embedder` protocol + deterministic `HashingEmbedder`.
  Placeholder semantics; swap a real model in Phase 7 behind the protocol.
- `tables.py` — pa-memory's OWN `Base`/metadata (separate from pa-knowledge's
  `SQLModel.metadata`): `memory_decision` + `memory_outcome` + `runtime_session` +
  `runtime_event` + `workspace` + `workspace_config` + `connector_config` +
  `preference` + `workflow_definition`, full JSON payloads.
- `store.py` — `DecisionStore(session, workspace="default")`: persist/read
  records, scoped to `workspace`. The session is **injected** by the app
  boundary; this package never builds an engine and never imports pa-knowledge.
- `service.py` — `LearningService(store, embedder)`: the agent-facing face
  (`relevant_lessons`/`record_decision`/`record_outcome`/`decisions`).
- `event_store.py` — `EventStore(session, workspace="default")`: append-only
  execution log (`runtime_session` + `runtime_event`). Persists **primitive**
  rows (session_id/seq/type/ts/JSON payload) — it does NOT import the
  platform's Event vocabulary (pa-memory stays below pa-platform). Serialization
  lives in `productagents.platform.serialization`. **Sessions are scoped to
  workspace**: every write stamps it, and the list read (`sessions()`) filters
  on it; a single get/update by `session_id` (`get_session`, `update_status`)
  does not — the id is already globally unique, so a workspace filter would be
  redundant. **Events are** likewise read by `session_id` (no workspace
  filtering on event reads) for the same reason.
- `workspace_state.py` — the workspace-state stores, all session-injected like
  the above: `WorkspaceRegistry(session)` — the `workspace` table itself (one
  row per project/team scope; `list`/`get`/`create`/`ensure`).
  `WorkspaceConfigStore(session, workspace)` / `ConnectorConfigStore(session,
  workspace)` — the six pipeline tunables / connector config blocks, scoped by
  composite primary key `(workspace, key)` / `(workspace, connector)`.
  `PreferenceStore(session)` — **deliberately unscoped**: preferences (e.g.
  theme) are a user-level UX setting, not workflow-execution state, so they
  follow the person across workspaces rather than resetting on every switch.
  `WorkflowDefinitionStore(session, workspace)` — CRUD over saved workflow
  definitions, scoped by composite primary key `(workspace, name)`; round-trips
  `WorkflowDefinition` (pa-core) through the row's JSON `payload` (the one store
  that returns a pydantic model rather than dicts, matching `DecisionStore`'s
  pattern). `list()` orders default-first then alphabetical; `save()` preserves
  an existing row's `is_default` unless overridden; `delete()` rejects `builtin`
  rows; `set_default()` clears other defaults atomically; `ensure_default()` is
  the idempotent seed used at startup (no-ops once the workspace has any row).

## Rules that matter
- **Sibling-layer boundary:** pa-memory imports only `pa-core` (+ sqlalchemy).
  It must NOT import `productagents.knowledge` (engine/session come injected).
- **Reflection stays in pa-agents** (`agents/reflection.py`): producing an
  `OutcomeRecord` needs an LLM call (`invoke_structured`), which pa-memory may
  not import. pa-memory only *stores* the outcome.
- **`__init__.py` must NOT re-export `event_store`** (same reason as
  `store`/`tables`: keep sqlalchemy out of `import productagents.memory`).
- **Schema changes go through pa-memory's own Alembic** (`uv run alembic upgrade
  head` from `packages/pa-memory`; `version_table="alembic_version_memory"` so
  it shares the DB file with pa-knowledge without clobbering its history).
  Alembic head is now `0005_workflow_definition` (`0001_memory_tables` →
  `0002_event_store` adds `runtime_session`/`runtime_event` →
  `0003_workspace_state` adds `workspace_config`/`connector_config`/
  `preference` → `0004_workspace_scope` creates the `workspace` registry
  table, adds a `workspace` column to `memory_decision`/`memory_outcome`/
  `runtime_session`, and widens `workspace_config`/`connector_config`'s
  primary key to `(workspace, key)`/`(workspace, connector)` →
  `0005_workflow_definition` adds the `workflow_definition` table, keyed
  `(workspace, name)`).
