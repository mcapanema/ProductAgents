# productagents.memory — organizational memory subsystem

Two halves the v1 code already names: **injection** (read lessons into a
decision) and **capture** (record outcomes after the fact). DB-backed since
Phase 6; JSONL demoted to export/audit.

## Layout
- `__init__.py` — re-exports ONLY the lightweight pure API (`jsonl` +
  `select_relevant_lessons`). **Never** re-export `service`/`store`/`tables`/
  `embedding`: that would pull SQLAlchemy into `import productagents.memory` and
  break the agents→storage import contract. Import those from their submodules.
- `jsonl.py` — append-only `decisions.jsonl`/`outcomes.jsonl` (export/audit).
- `retrieval.py` — lexical ranker (`select_relevant_lessons`, validated-first /
  derived-second + dedup) plus `cosine`/`semantic_matches`. The `also_relevant`
  set lets zero-lexical-overlap decisions in via the semantic path.
- `embedding.py` — `Embedder` protocol + deterministic `HashingEmbedder`.
  Placeholder semantics; swap a real model in Phase 7 behind the protocol.
- `tables.py` — pa-memory's OWN `Base`/metadata (separate from pa-knowledge's
  `SQLModel.metadata`): `memory_decision` + `memory_outcome`, full JSON payloads.
- `store.py` — `DecisionStore(session)`: persist/read records. The session is
  **injected** by the app boundary; this package never builds an engine and
  never imports pa-knowledge.
- `service.py` — `LearningService(store, embedder)`: the agent-facing face
  (`relevant_lessons`/`record_decision`/`record_outcome`/`decisions`).

## Rules that matter
- **Sibling-layer boundary:** pa-memory imports only `pa-core` (+ sqlalchemy).
  It must NOT import `productagents.knowledge` (engine/session come injected).
- **Reflection stays in pa-agents** (`agents/reflection.py`): producing an
  `OutcomeRecord` needs an LLM call (`invoke_structured`), which pa-memory may
  not import. pa-memory only *stores* the outcome.
- **Schema changes go through pa-memory's own Alembic** (`uv run alembic upgrade
  head` from `packages/pa-memory`; `version_table="alembic_version_memory"` so
  it shares the DB file with pa-knowledge without clobbering its history).
