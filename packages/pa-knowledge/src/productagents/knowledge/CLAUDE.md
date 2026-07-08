# productagents.knowledge — storage & services

This package has two layers: the **storage spine** and, built on top of it,
the **knowledge services** (the platform API).

## What's here

- `config.py` — `database_url()` (`PRODUCTAGENTS_DB_URL`, default local SQLite).
- `sink.py` — `CanonicalSink` protocol + `DbCanonicalSink`. **Connectors write
  here** and stay storage-ignorant; the sink routes each model to a repository
  by `type(model)`.
- `sync_state.py` — `SyncStateStore(session, workspace="default")`:
  per-connector incremental cursor persistence (`sync_state` table), scoped to
  `workspace`. Cursors are **plain strings**, never `SyncCursor`, so storage
  never imports a connector type. The app converts.
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
  - `canonical_repository.py` — `CanonicalRepository[T](session, model_type,
    workspace="default")`. Upsert dedups on `(workspace, connector, vendor_type,
    vendor_id)` for synced records, on the platform id (checked against
    `self._workspace`) for manual ones, and **keeps the original platform id
    stable across re-syncs**.
- `alembic/` — migrations (source of truth for the schema). `env.py` is async and
  reads the URL from `database_url()`.

### Services

- `services/_page.py` — `Page[T]`: typed pagination result (`items`/`total`/
  `limit`/`offset` + `has_more`).
- `services/_query.py` — `Query[T]` base: `limit`/`offset` + a pure
  `matches(model) -> bool` predicate. Subclass it per service, add filter fields,
  override `matches`.
- `services/_service.py` — `CanonicalQueryService[T]`: `get(id)` + `search(query)`.
  `search` scans the type partition and filters/paginates **in Python** —
  honest at local-first scale; the upgrade path (push the predicate into the
  repository) is marked with a `ponytail:` comment.
- `services/{feedback,initiative,metrics}_service.py` — the three concrete
  services + their `*Query` types. Roadmap/Strategy/Risk services are deferred
  until a consumer is concrete (YAGNI); they are the same two-class shape.
- `container.py` — `KnowledgeServices` bundle + `build_services(session,
  workspace="default")`. This is the DI assembly (every repository it builds
  is scoped to `workspace`); `pa-platform`'s `context.py` (`open_agent_context()`)
  wraps it + the chat model into `AgentContext`.

**Service rules:** services depend on the `Repository[T]` *protocol*, never on a
concrete repo, a session, or `CanonicalRecord` (only `container.py` constructs
repositories). Add a service method only when an agent need is concrete, never
speculatively. Unit-test services with `tests/knowledge_fakes.py::FakeRepository`;
test the container against the real in-memory store.

## Rules that matter

- **Repositories are the only thing that touches storage.** Nothing above
  (agents, app) imports `repositories`/`sqlmodel`/`alembic`.
- **Manual records map empty `vendor_id` → NULL** so they never collide on the
  unique constraint.
- **`pa-core` never imports SQLAlchemy.** The table model is a *separate* type
  from the canonical model; mapping is explicit.
- **Schema changes go through Alembic** (`uv run alembic revision --autogenerate`
  from `packages/pa-knowledge`, review, commit). `create_all` is test-only (and
  the one-time shared-home bootstrap, see root CLAUDE.md's ponytail note on
  `bootstrap.py`). Head is now `0004_tz_aware_datetimes` (`0001_canonical_record` →
  `0002_sync_state` adds the `sync_state` table → `0003_workspace_scope` adds a
  `workspace` column to `canonical_record`/`sync_state`, widening their unique
  key / primary key to include it → `0004_tz_aware_datetimes` makes
  `ingested_at`/`updated_at` timezone-aware `DateTime` columns).
