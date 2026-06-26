# productagents.knowledge — storage & (later) services

Phase 2 implements the **storage spine**. Services (Phase 3) will sit on top.

## What's here

- `config.py` — `database_url()` (`PRODUCTAGENTS_DB_URL`, default local SQLite).
- `sink.py` — `CanonicalSink` protocol + `DbCanonicalSink`. **Connectors write
  here** and stay storage-ignorant; the sink routes each model to a repository
  by `type(model)`.
- `repositories/_base.py` — `Repository[T]` protocol (`get`/`upsert`/`list`).
  Services depend on this, never on a concrete impl, so SQLite↔Postgres is a
  driver swap and tests inject fakes.
- `repositories/sqlmodel/` — the one concrete impl:
  - `engine.py` — async engine + session factory (`aiosqlite`; `StaticPool` for
    in-memory so tests survive session churn).
  - `tables.py` — `CanonicalRecord`, the **single generic table**: lineage/sync
    fields are columns; domain fields live verbatim in the JSON `payload`.
  - `mapping.py` — pure `to_row`/`from_row`. `from_row` validates `payload`, so
    round-trips are byte-stable.
  - `canonical_repository.py` — `CanonicalRepository[T]`. Upsert dedups on
    `(connector, vendor_type, vendor_id)` for synced records, on the platform id
    for manual ones, and **keeps the original platform id stable across re-syncs**.
- `alembic/` — migrations (source of truth for the schema). `env.py` is async and
  reads the URL from `database_url()`.

## Rules that matter

- **Repositories are the only thing that touches storage.** Nothing above
  (agents, app) imports `repositories`/`sqlmodel`/`alembic`.
- **Manual records map empty `vendor_id` → NULL** so they never collide on the
  unique constraint.
- **`pa-core` never imports SQLAlchemy.** The table model is a *separate* type
  from the canonical model; mapping is explicit.
- **Schema changes go through Alembic** (`uv run alembic revision --autogenerate`
  from `packages/pa-knowledge`, review, commit). `create_all` is test-only.
