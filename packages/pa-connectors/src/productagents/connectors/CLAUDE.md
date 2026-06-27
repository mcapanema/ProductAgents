# productagents.connectors — Layer-1 connector framework

Connectors extract from external systems, **map vendor records → canonical
models** (one-way, pure mappers), and push them to a `CanonicalSink`. They are
the only place that knows a vendor exists.

## What's here

- `base.py` — the `Connector` ABC + value types (`SyncCursor`, `SyncResult`,
  `HealthStatus`, `ConnectorConfig`) + the `CanonicalSink` **Protocol** the
  connector writes to. The concrete sink (`DbCanonicalSink`) lives in
  `pa-knowledge` and satisfies this Protocol structurally — connectors never
  import the storage layer.
- `http.py` — `make_client()` (bearer auth + headers + timeout) and
  `request_with_retry()` (retry transient `{429,5xx}` + transport errors).
  Provider-agnostic; every connector shares it.
- `registry.py` — `discover()`: entry-point (`productagents.connectors`) lookup,
  `key → class`. A `pip install`ed third-party connector self-registers here.
- `runtime.py` — `run_sync()`: runs enabled connectors concurrently under a
  `TaskGroup`, catching each failure into a degraded `SyncResult` (never aborts
  the batch). Cursors are threaded, **not persisted** (no scheduler yet — Phase 7).
- `github/` — the first connector: `connector.py` (`GitHubConfig` +
  `GitHubConnector`), `client.py` (paginated issue fetch, `since` cursor),
  `mappers.py` (`issue_to_feedback`).
- `jira/` — the second connector: `connector.py` (`JiraConfig` + `JiraConnector`,
  Basic auth via the `make_client(headers=...)` seam), `client.py` (`/rest/api/3/search`
  enhanced search, `nextPageToken` pagination, JQL `updated` cursor), `mappers.py`
  (`issue_to_feedback`, ADF-description flattening).

## Rules that matter

- **`pa-connectors` imports only `pa-core` + `httpx`** (+ stdlib). Never
  `pa-knowledge`/`pa-agents`/`pa-app`/`pa-memory`/sqlalchemy/langchain —
  enforced by `lint-imports`. The sink is a Protocol defined *here*.
- **Connectors degrade, never crash.** `health_check` and `sync` wrap every
  network boundary and return a result; the runtime relies on this.
- **Mappers keep vendor terms out of domain fields.** Vendor identity goes on
  `SourceRef` only; `tests/canonical_harness.py` enforces no leakage.
- **Self-register via entry points**, not import-time side effects — discovery
  stays metadata-only (no httpx import to list connectors).
- **Tests are offline.** Mock httpx with `respx`; use `tests/connector_fakes.py`
  (`FakeSink`) instead of a real store for unit tests.

## Deferred (YAGNI, named upgrade paths)

- **YAML** connector config — SHIPPED in Phase 7a (`pa-app/sync.py` loads
  `connectors.yaml`; each connector declares `config_cls` and the app validates
  blocks generically). Cursor **persistence** (`sync_state` table +
  `SyncStateStore`) also shipped in Phase 7a.
- A `connector_errors.py` category classifier — Phase 7c, when observability
  surfaces categories. Today: a transient-status set in `http.py`.
