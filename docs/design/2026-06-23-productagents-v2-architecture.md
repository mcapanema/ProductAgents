# ProductAgents v2 — Architecture Review & System Design

> Staff+ architecture review. This document is the design contract that
> precedes implementation plans. It does **not** generate code. Implementation
> plans (one per phase) are derived from §14 after the open decisions in the
> appendix are resolved.

**Framing:** ProductAgents is a *product-decision operating system*. Agents are
the first consumer of the platform, not the platform itself. Everything below
optimizes for the day there is a second consumer (a REST API, a scheduled
portfolio review, a Slack bot) that reuses the same Knowledge Layer without
touching agent code.

The guiding invariant, repeated everywhere:

```
Agents → Knowledge Services → Canonical Models → Connectors → External Systems
         (the platform API)    (the vocabulary)   (the ETL)    (vendors)
```

Each arrow is a **one-way dependency**. Nothing below an arrow may import
anything above it. This is the single rule that keeps the platform organization-
agnostic.

---

## 0. What exists today (the slice we evolve, not discard)

The current repo is a clean ~2,500-LOC vertical slice with strong bones we keep:

- `schemas.py` — Pydantic models, already split into *LLM-output* schemas vs
  *assembled records*. The v2 canonical models are a superset of these.
- `graph.py` / `runner.py` — the orchestration↔UI boundary. **This is already
  the Agent↔platform seam done right**: agents emit typed events, the UI knows
  no LangGraph. v2 generalizes `runner` into a platform entry point.
- `memory.py` — JSONL append-only Organizational Memory stub with lexical lesson
  retrieval. v2 promotes this to a real subsystem (the Learning Service).
- `evidence.py` — the `EvidenceSource` protocol is a proto-connector. v2
  reframes it: today evidence is read live from files; v2 reads it from the
  Knowledge Layer, which is fed by connectors out-of-band.

**Decision posture:** *evolve in place*, not greenfield. The slice proves the
agent loop works; v2 slides the three data layers *underneath* it. Agents change
the least of anything in the system.

---

## 1. Project structure

```
ProductAgents/
├── pyproject.toml                 # workspace root (uv workspace)
├── packages/
│   ├── pa-core/                   # canonical models, config, errors, types
│   │   └── src/productagents/core/
│   ├── pa-connectors/             # connector framework + first-party connectors
│   │   └── src/productagents/connectors/
│   ├── pa-knowledge/              # knowledge services + storage/repositories
│   │   └── src/productagents/knowledge/
│   ├── pa-memory/                 # organizational memory subsystem
│   │   └── src/productagents/memory/
│   ├── pa-agents/                 # LangGraph nodes, graph assembly, runner
│   │   └── src/productagents/agents/
│   └── pa-app/                    # TUI + CLI entry points (the "edge")
│       └── src/productagents/app/
├── docs/design/                   # this doc + ADRs
└── docs/superpowers/plans/        # phase implementation plans
```

All packages share the `productagents.*` import namespace (PEP 420 namespace
packages) so imports stay clean (`from productagents.core.models import
Initiative`) while distribution boundaries stay enforceable.

**Why a uv workspace and not one flat package?** The spec demands a
marketplace-style connector ecosystem and "adding a connector must not modify
core code." A workspace makes the dependency *physically* enforceable: `pa-core`
declares zero dependency on `pa-connectors`, so a connector importing a
canonical model compiles, but core importing a connector does not. Distribution
also becomes possible later (`pip install productagents-connector-jira`) without
re-architecting.

**Tradeoff:** a workspace adds ceremony (multiple `pyproject.toml`, intra-repo
path deps) before it pays off. We mitigate by starting with the *layout* but a
*single lockfile* (uv workspace shares one lock), so day-1 ergonomics ≈ a single
package, while the seams are already drawn.

**Alternative considered — single package, enforce layers with import-linter:**
lighter to start, but boundaries are advisory (a lint rule someone disables),
not structural, and you can never split a connector out for independent release.
Rejected for a platform explicitly aiming at a marketplace.

**Alternative considered — full polyrepo:** maximum isolation, but premature;
cross-cutting refactors (every layer at once, which v1→v2 is) become painful.
Workspace gives 80% of the isolation with one-repo refactor ergonomics.

---

## 2. Package structure & dependency direction

```
pa-app  ─────────────┐
   │ (depends on)     │
   ▼                  ▼
pa-agents        (CLI/REST later)
   │
   ▼
pa-knowledge ──► pa-memory
   │                │
   ▼                ▼
pa-core ◄───────────┘   (everyone depends on core; core depends on nothing)
   ▲
   │
pa-connectors ──► pa-core   (connectors map INTO core models; nothing imports a connector by name)
```

Hard rules, enforced in CI by `import-linter` contracts:

- `pa-core` imports only stdlib + pydantic. No httpx, no langchain, no DB driver.
- `pa-connectors` imports `pa-core` (to emit canonical models) + httpx. **Never**
  imports `pa-knowledge` or `pa-agents`.
- `pa-knowledge` imports `pa-core` + the storage layer. **Never** imports a
  concrete connector or `pa-agents`.
- `pa-agents` imports `pa-knowledge` + `pa-core` + langgraph. **Never** imports a
  connector or a DB driver directly — agents get data only through services.
- `pa-app` is the only package allowed to wire everything (composition root).

**Why this scales:** the dependency graph is a DAG with `pa-core` as the sink.
New connectors and new services are leaves; they never force a change above
them. The "agents reason about concepts, never vendors" invariant becomes a
*compile-time* property, not a code-review hope.

---

## 3. Domain model organization (Canonical Models — Layer 2)

This is the heart of the platform. Organize `pa-core` by *bounded context*, not
by one giant `schemas.py`:

```
productagents/core/
├── models/
│   ├── _base.py          # CanonicalModel base, identifiers, provenance mixin
│   ├── discovery.py      # CustomerFeedback, SupportTicket, UserSegment, Incident
│   ├── planning.py       # Initiative, Feature, RoadmapItem
│   ├── strategy.py       # Objective, KeyResult
│   ├── measurement.py    # ProductMetric, MetricSnapshot
│   └── decision.py       # DecisionRecord, DebateTranscript, RiskAssessment, Recommendation
├── refs.py               # SourceRef, ExternalRef (provenance/lineage)
├── ids.py                # typed IDs (InitiativeId = NewType / branded str)
└── enums.py              # shared Literals/Enums (Priority, RiskLevel, Verdict)
```

### The base every canonical model shares

```python
class CanonicalModel(BaseModel):
    id: CanonicalId                 # platform-owned, stable, not the vendor id
    source: SourceRef               # which connector + which vendor record
    ingested_at: datetime
    updated_at: datetime
    raw_fingerprint: str | None     # hash of source payload, for incremental sync
```

**`SourceRef` is the lineage spine.** Every canonical record knows the connector,
the vendor entity type, and the vendor id it was mapped from — *but agents never
read those fields for reasoning*. They exist for traceability, dedup, and sync
reconciliation. This is how a `Initiative` can be sourced from Jira *or* Linear
and an agent cannot tell which.

**Why typed IDs (`InitiativeId`, not `str`):** prevents the entire class of bug
where a feedback id is passed where an initiative id is expected. Cheap with
`typing.NewType`; pydantic validates them. Scales because cross-references
between models (a `RoadmapItem.initiative_id`) become self-documenting and
type-checked.

**Mapping direction is strict:** vendor → canonical happens *only* inside a
connector's mapper. `core` has no knowledge a Jira exists. A mapper is a pure
function `JiraIssue → Initiative` living in `pa-connectors/jira/mappers.py`. The
canonical model has no `from_jira()` constructor — that would invert the
dependency.

**Tradeoff — richness vs lowest-common-denominator:** if `Initiative` only holds
fields every tool has, it's anemic; if it holds every field any tool has, it's a
union dumping ground. Resolution: canonical models hold the *product concept's*
intrinsic fields; vendor-specific extras go in a typed `extensions: dict[str,
JsonValue]` escape hatch that agents are documented never to reason over. This
keeps the model honest without losing data.

**Alternative considered — protobuf/Avro schemas:** strong cross-language
contracts and versioning, but the platform is Python-only and pydantic gives us
validation + JSON + LangChain structured-output for free. Revisit only if a
non-Python connector ecosystem emerges.

---

## 4. Connector framework design (Layer 1)

```
productagents/connectors/
├── base.py            # Connector ABC, ConnectorContext, SyncResult
├── registry.py        # entry-point discovery + enabled-connector resolution
├── runtime.py         # async sync orchestration (concurrency, retries, cursors)
├── http.py            # shared httpx client factory (timeouts, rate-limit, auth)
└── jira/ linear/ zendesk/ ...   # one subpackage per connector
        ├── connector.py   # implements Connector
        ├── client.py      # httpx calls: auth, pagination, rate limiting
        └── mappers.py      # VendorEntity → CanonicalModel (pure functions)
```

### The contract

```python
class Connector(ABC):
    key: ClassVar[str]                       # "jira", unique, used in config
    produces: ClassVar[frozenset[type[CanonicalModel]]]  # what it can emit

    def __init__(self, config: ConnectorConfig, sink: CanonicalSink): ...

    @abstractmethod
    async def health_check(self) -> HealthStatus: ...

    @abstractmethod
    async def sync(self, cursor: SyncCursor | None) -> SyncResult:
        """Extract since `cursor`, map to canonical, write via `sink`,
        return a new cursor. Idempotent on re-run."""
```

Key design choices:

- **Connectors push to a `CanonicalSink`, they don't return data.** The sink
  (provided by `pa-knowledge`) handles upsert/dedup keyed on
  `(connector_key, vendor_id)`. This keeps connectors ignorant of storage and
  lets sync stream large datasets without buffering everything in memory.
- **`SyncCursor` enables incremental sync.** Persisted per connector; a cursor is
  an opaque vendor-shaped token (a timestamp, an updated-since marker, an opaque
  page token). The runtime stores it; the connector interprets it.
- **`produces` makes the registry queryable**: the Metrics Service can ask "which
  enabled connectors produce `ProductMetric`?" without naming Mixpanel.

### Self-registration & discovery

Use Python **entry points** (`[project.entry-points."productagents.connectors"]`)
not import-time side effects. The registry enumerates installed entry points and
filters by config-enabled keys. This is exactly the marketplace seam: a
third-party `pip install productagents-connector-foo` registers itself with zero
core changes.

**Tradeoff vs a decorator registry** (`@register`): decorators require importing
the module (and thus its deps) just to discover it; entry points are
metadata-only discovery — you can list available connectors without importing
their httpx/SDK deps. Worth the slightly more verbose packaging.

**Why async/httpx (hard requirement honored):** sync jobs are I/O-bound and
concurrent across connectors. The `runtime` runs enabled connectors under an
`asyncio.TaskGroup` with a per-connector concurrency cap and a shared rate-limit-
aware httpx client. No `requests`, anywhere — enforced by an import-linter
forbidden-module contract.

**Error handling reuses the v1 pattern:** the existing `llm_errors.py`
classifier (categorize by status/class/message, `fatal` flag, degrade-don't-
crash) generalizes to a `connector_errors.py`. A connector failure degrades that
connector's sync and surfaces in observability; it never aborts the platform.

---

## 5. Knowledge Service architecture (Layer 3 — the platform API)

This is what agents see. **Services expose product questions, not tables.**

```
productagents/knowledge/
├── services/
│   ├── feedback_service.py     # search(), get(), find_related_to_initiative()
│   ├── initiative_service.py   # get(), list(), search()
│   ├── roadmap_service.py
│   ├── metrics_service.py      # find_related(), snapshot()
│   ├── strategy_service.py     # objectives(), key_results_for()
│   └── risk_service.py
├── repositories/               # storage access; one per aggregate
│   ├── _base.py                # Repository[T] protocol
│   └── sqlmodel/ ...           # concrete impl (see §6)
├── sink.py                     # CanonicalSink impl (connectors write here)
└── container.py                # service factory / DI assembly
```

### Service shape

```python
class FeedbackService:
    def __init__(self, repo: FeedbackRepository, search: SearchIndex): ...

    async def search(self, query: FeedbackQuery) -> Page[CustomerFeedback]: ...
    async def get(self, id: FeedbackId) -> CustomerFeedback | None: ...
    async def find_related(self, initiative: InitiativeId,
                           limit: int = 20) -> list[CustomerFeedback]: ...
```

- **Inputs and outputs are typed canonical models** (and typed *query* objects,
  not kwargs soup). `FeedbackQuery` is itself a pydantic model — segment,
  time window, sentiment, free text — so the agent↔service contract is
  introspectable and stable.
- **Services compose repositories + a search index**, deciding *where* data comes
  from (hot store, search index, memory subsystem). The agent never knows. This
  is the literal realization of "the service decides where data comes from."
- **Repositories are the only thing that touches storage.** Swapping SQLite for
  Postgres changes a repository, not a service, and never an agent.

**Why this scales:** services are the platform's public API and its stability
contract. Connectors and storage churn below; agents and future consumers (REST,
jobs) sit above; the service signature is the membrane. New consumers reuse
services for free — which is the whole "platform, not agent project" thesis.

**Tradeoff — service granularity:** too many micro-methods → a sprawling API;
too few god-methods → leaky `**filters`. Resolution: one typed `Query` object
per service + a small set of intention-revealing methods (`find_related`,
`search`, `get`, `list`). Add methods when an agent need is concrete, never
speculatively (YAGNI).

**Alternative considered — agents query a repository/ORM directly:** less
indirection now, but it welds agents to the schema and kills the "never know
where data came from" guarantee. Rejected — it collapses Layer 2 and 3.

**Alternative considered — GraphQL gateway as the knowledge layer:** great for
external clients, overkill for in-process agents and adds a serialization hop.
Keep services as in-process Python now; a GraphQL/REST facade can wrap them later
*because they're already a clean API*.

---

## 6. Database architecture

Three logical stores, one engine to start:

| Store | Holds | Access pattern |
| --- | --- | --- |
| **Canonical store** | synced canonical models (Initiative, Feedback, …) | upsert by sync, read by services |
| **Memory store** | DecisionRecords, outcomes, embeddings | append + similarity search |
| **Sync state** | cursors, connector run history, health | small, transactional |

**Recommendation: SQLAlchemy 2.0 async (`asyncio` engine) over SQLite for
local-first, Postgres for scale — same code path.** Use **SQLModel** (pydantic +
SQLAlchemy) so canonical models and persistence share one type system.

- Local/default: **SQLite via `aiosqlite`** — zero-ops, file-based, matches the
  current JSONL "just works locally" ethos and the "operate on local normalized
  data" requirement.
- Scale/team: **Postgres via `asyncpg`** — same SQLAlchemy core, swap the URL.
- **Vector similarity** for memory: `sqlite-vec` extension locally; `pgvector` on
  Postgres. The Learning Service depends on a `VectorIndex` protocol so the
  backend is swappable.

**Why not keep JSONL?** It can't do incremental upsert, secondary-index lookup,
or similarity search — all of which §5/§7 need. JSONL stays as an *export/audit*
format, not the query store.

**Repositories isolate the engine choice.** Services depend on repository
*protocols*; the `sqlmodel/` implementations are injected. Tests inject in-memory
fakes (continuing the `FakeChatModel` discipline). Migrating SQLite→Postgres is a
config + driver change, not a service change.

**Migrations:** Alembic from day one (even on SQLite). Canonical models *will*
evolve; the read side already tolerates schema drift (v1 `_read_jsonl` skips
incompatible lines) — Alembic makes that intentional instead of lossy.

**Tradeoff — SQLModel vs raw SQLAlchemy vs raw SQL:** SQLModel risks coupling the
domain model to the table model. Mitigation: keep *pure* canonical models in
`pa-core` (no SQLAlchemy import there — core stays dependency-free) and define
*table* models in `pa-knowledge/repositories/sqlmodel/` that map to/from them.
Costs one mapping layer; buys a dependency-free core and swappable storage.
(If that mapping proves to be pure boilerplate in practice, collapsing it is a
later, reversible call.)

**Alternative considered — DuckDB:** excellent for the analytical/"historical
analysis" workload, but weaker for transactional upsert during sync. Candidate
*later* as a read-replica/analytics store fed from the canonical store, not the
primary.

**Alternative considered — a dedicated vector DB (Qdrant/Chroma):** more capable
similarity search, but a second service to run breaks local-first. `sqlite-vec`/
`pgvector` keep one engine; revisit at corpus scale.

---

## 7. Organizational Memory architecture (first-class subsystem)

Promote `memory.py` from a JSONL stub to `pa-memory`, a real subsystem with two
halves the v1 code already names: **injection** (read lessons into a decision)
and **capture** (record outcomes after the fact).

```
productagents/memory/
├── models.py          # DecisionArtifact, OutcomeRecord, Lesson (canonical, in core)
├── store.py           # DecisionStore: persist full decision artifacts
├── retrieval.py       # LessonRetriever: lexical + vector hybrid
├── reflection.py      # outcome capture (the v1 reflection agent, generalized)
└── learning_service.py# the Knowledge-Layer face: relevant_lessons(), record_outcome()
```

- **Every decision persists a complete `DecisionArtifact`**: evidence refs,
  analyst reports, debate transcript, recommendation, risk assessment, judge
  verdict, approval decision, predicted outcomes — the full provenance graph, not
  a summary. This is the "persistent artifact per decision" requirement, typed.
- **Retrieval is hybrid**: keep v1's lexical overlap (it's interpretable and
  needs no model) as a baseline, *add* embedding similarity over initiative text
  for semantic recall. v1's validated-first / derived-second ranking and dedup
  logic ports directly — it's already good.
- **The learning loop closes through the graph** exactly as today: a `recall`
  node calls `LearningService.relevant_lessons(initiative)`; the strategist gets
  them injected. Capture stays out-of-graph (reflection), as it is now.
- **Outcomes link predicted→actual** via `decision_id`, enabling the platform's
  real goal: measuring prediction accuracy over time and feeding it back as
  weighting on future lessons.

**Why a subsystem, not a service method:** memory has its own storage, its own
embedding lifecycle, its own retrieval policy, and is consumed by both agents
*and* (future) analytics. Burying it inside `initiative_service` would re-entangle
concerns. It exposes itself to agents *as* a Knowledge Service
(`LearningService`), preserving the uniform agent-facing API.

**Tradeoff — store full artifacts (heavy) vs summaries (lossy):** full artifacts
cost storage but are the entire point ("learn from previous decisions" needs the
reasoning, not just the verdict). Storage is cheap; replayability is the asset.

---

## 8. LangGraph integration strategy

Keep the v1 architecture — it's already correct — and generalize three seams:

1. **Dependency injection of capabilities, not just the model.** Today nodes get
   a `model` via `partial`. v2 injects a typed `AgentContext` carrying the model
   *and* the Knowledge Services the node is allowed to use. Nodes still never
   construct dependencies; tests still inject fakes.

   ```python
   @dataclass(frozen=True)
   class AgentContext:
       model: BaseChatModel
       feedback: FeedbackService
       initiatives: InitiativeService
       metrics: MetricsService
       learning: LearningService
       # ... services, never connectors, never repositories
   ```

2. **Evidence comes from services, not files.** The v1 `evidence.py` live-file
   read is replaced by analysts calling services during their node. Crucially,
   this still honors "no external fetch during agent execution" — services read
   the *local canonical store*, which connectors populated out-of-band.

3. **Graph assembly stays declarative and model-injected.** `build_graph(context,
   *, human_in_the_loop=False)` mirrors today's `build_graph(model, ...)`. The
   parallel-analyst fan-out, `operator.add` reducer, judge retry loop, and HITL
   interrupt/checkpointer all carry over unchanged.

**Why minimal change:** the v1 graph is the part that already embodies the target
architecture (typed state, degrade-don't-crash, UI-agnostic events). The v2 work
is *beneath* it. Over-rewriting the graph would be churn for its own sake.

**Tradeoff — `AgentContext` as one bag vs per-node narrow interfaces:** a single
context is convenient but lets any node touch any service. Mitigation: type each
node's signature to the slice it needs (`market_node(state, *, ctx:
MarketContext)`), where `MarketContext` is a `Protocol` exposing only the
services that node may use — least privilege, still one assembly.

---

## 9. Agent integration strategy

- **Agents are the *reference* consumer of the Knowledge Layer, not a privileged
  one.** Anything an agent can do, the REST API or a batch job can do, through the
  same services. This is the test of whether the platform thesis holds.
- **Agent I/O stays fully typed**, extending today's discipline: typed structured
  outputs (`AnalystFindings`, `Recommendation`, …) and now typed *inputs* (the
  `Query` objects and canonical models from services).
- **The `runner.py` event boundary becomes the platform's streaming protocol.**
  Today it serves the TUI; v2 keeps the dataclass events and lets *any* edge
  (TUI, CLI, SSE/WebSocket for a future web UI) subscribe. The agents layer emits
  events; edges render them. No edge knows LangGraph.
- **MCP lives at the agent edge, for tools — never for data.** A node may call an
  MCP tool for ad-hoc retrieval (Confluence search, GitHub exploration, browser),
  but synced product data always comes through Knowledge Services. Enforced by
  layering: MCP tool clients live in `pa-agents`, the connector framework in
  `pa-connectors`, and they never meet. "MCP for tools, connectors for data" is a
  package boundary, not a guideline.

---

## 10. Configuration strategy

Layered, typed, and validated at startup:

```
productagents/core/config/
├── settings.py     # AppSettings (pydantic-settings): env + .env
├── connectors.py   # ConnectorConfig models (per-connector typed schema)
└── loader.py       # merge: defaults < config file (YAML) < env < runtime
```

- **`pydantic-settings`** for the typed, validated settings object — extends the
  v1 env-var approach (`PRODUCTAGENTS_*`) without abandoning it.
- **Connectors enabled via a YAML file** (the spec's `connectors:` block), but
  each connector contributes a **typed config schema** validated at load. Secrets
  (tokens) come from env/secret manager and are *referenced* by the YAML, never
  inlined.

  ```yaml
  connectors:
    jira:
      enabled: true
      base_url: https://acme.atlassian.net
      auth: { token_env: JIRA_TOKEN }
      projects: [PROD, GROWTH]
    zendesk:
      enabled: false
  ```

- **Validation is fail-fast and friendly** — reuse the v1 `check_config` /
  SetupScreen ethos: an enabled connector with a missing token is caught at
  startup with a clear message, not at first sync.
- **Marketplace-ready:** because each connector self-describes its config schema
  (a classmethod returning a pydantic model), the platform can render setup UIs
  and validate third-party connectors it has never heard of.

**Tradeoff — YAML vs all-env:** env-only is 12-factor-clean but unreadable for
nested per-connector config; YAML is readable but needs a secrets discipline.
Resolution above: YAML for structure, env for secrets, typed merge for both.

---

## 11. Dependency management strategy (uv)

- **uv workspace** (`[tool.uv.workspace]`) with one root lockfile; member packages
  declare intra-repo deps as workspace sources. One `uv sync` for the whole repo.
- **Connectors are optional extras**, not core deps: `pa-connectors` exposes
  extras (`productagents[jira,zendesk]`) so a deployment installs only the
  connectors it enables. Core never pulls vendor SDKs.
- **Dependency-group discipline** continues from v1 (`dev` group for
  pytest/ruff/ty/bandit). Add a `docs` group later if needed.
- **Floors, not pins**, for libraries; the lockfile pins exact versions for
  reproducibility. Keeps the v1 Dependabot/pip-audit/bandit CI posture.
- **Python ≥ 3.14, async-first, httpx everywhere** — `requests` added to a
  forbidden-imports contract so it can't sneak in.

**Why a workspace lock:** reproducible cross-package builds and atomic upgrades;
a connector and core can't drift to incompatible transitive versions.

**Tradeoff:** workspace tooling is younger than Poetry-style monorepos, but uv is
already the project's chosen tool and its workspace support is first-class and
fast. Staying in one toolchain beats mixing.

---

## 12. Testing strategy

Extend the v1 doctrine (fully offline, fakes, ≥90% coverage) layer by layer:

| Layer | Strategy |
| --- | --- |
| **Canonical models** | pure pydantic validation tests; mapper round-trip tests (vendor fixture → canonical, asserting no vendor leakage) |
| **Connectors** | httpx mocked via `respx`/`httpx.MockTransport`; **never** hit a live API in CI. Test pagination, rate-limit backoff, incremental cursor, and mapping. Fixtures are recorded vendor payloads. |
| **Knowledge services** | inject fake repositories (in-memory) — services tested with zero DB. Repository contract tests run against real SQLite (fast, file-based). |
| **Memory** | retrieval ranking tests (port v1's), embedding tests against a fake/local embedder, capture round-trip. |
| **Agents** | keep `FakeChatModel`; now also inject **fake services** into `AgentContext`. Node tests assert reasoning over canonical inputs, no I/O. |
| **Graph/runner** | build with fakes end-to-end, assert the event stream — exactly as today. |
| **Boundaries** | import-linter contracts run in CI as tests: a connector importing knowledge *fails the build*. The architecture is tested, not just hoped. |

**Principles preserved:** TDD per task, offline-by-default, `asyncio_mode=auto`,
coverage gate. The new rule: **every mapper and every service method ships with a
test that proves no vendor concept escapes its layer.**

---

## 13. Observability strategy

The spec lists "improved observability" as a *reason* for sync-before-execute, so
make it first-class:

- **Structured logging** generalizes v1's file-only `logging_config` (the TUI owns
  the terminal). Add structured (JSON) sink option for non-TUI edges. Keep
  `propagate=False`, rotating file.
- **OpenTelemetry traces** across the two long-lived flows: a **sync run** (span
  per connector, child spans per page/batch, attributes = records synced, rate-
  limit waits, errors) and a **decision run** (span per graph node, child spans
  per LLM/service call). One trace = one decision, end to end.
- **LangSmith/LangGraph tracing** for agent reasoning (LangChain-native, low
  effort) — complements OTel rather than replacing it.
- **Sync health surface**: `health_check()` results + last-cursor + last-error per
  connector, queryable (feeds a future ops dashboard and the setup UI).
- **Decision auditability is observability too**: the Organizational Memory
  artifact *is* the audit log of why a decision was made; OTel is the audit log of
  *how* the system executed.

**Tradeoff — OTel now vs later:** instrumenting from the start is cheap (a
decorator + context); retrofitting traces across async boundaries later is
painful. Adopt the API now, default the exporter to a no-op/console locally so
there's zero ops burden until someone wires a collector.

---

## 14. Recommended implementation roadmap

Sequenced so **each phase ships working, testable software** and the platform is
usable end-to-end as early as possible. Phases map 1:1 to implementation plans in
`docs/superpowers/plans/`.

> **Phase 0 — Workspace & boundaries (foundation).**
> Convert to the uv workspace, create the six packages, move v1 code into
> `pa-agents`/`pa-app`/`pa-core` with imports updated, add import-linter contracts
> + forbidden-imports (`requests`). *Deliverable:* the existing TUI runs
> unchanged; the architecture is now enforceable. No behavior change — pure
> structural, fully covered by the existing suite.

> **Phase 1 — Canonical models (Layer 2).**
> Build `pa-core/models` bounded contexts, `SourceRef`/typed IDs/`CanonicalModel`
> base. Migrate v1 schemas into it. *Deliverable:* the vocabulary the whole
> platform speaks, with validation + mapper round-trip test harness.

> **Phase 2 — Storage & repositories (Layer fundamentals).**
> SQLAlchemy-async + SQLModel table models, repository protocols + SQLite impls,
> Alembic, the `CanonicalSink`. *Deliverable:* canonical models persist and query
> locally; repository contract tests green.

> **Phase 3 — Knowledge Services (Layer 3, the API).**
> `FeedbackService`, `InitiativeService`, `MetricsService`, etc. over repositories;
> the `AgentContext`/`container`. *Deliverable:* the platform API exists and is
> tested with fake repos; not yet fed by real connectors.

> **Phase 4 — Connector framework + first connector.**
> `Connector` ABC, entry-point registry, async sync runtime, shared httpx client,
> connector error classifier, **one reference connector** (recommend a simple one
> first — e.g. a local/CSV or GitHub connector) end-to-end into the canonical
> store. *Deliverable:* `sync` populates the store; a service reads what a
> connector wrote. The full data spine is alive.

> **Phase 5 — Rewire agents onto Knowledge Services.**
> Replace `evidence.py` live-file reads with service calls inside analyst nodes;
> inject `AgentContext`. *Deliverable:* agents reason over synced canonical data;
> "no fetch during execution" holds; TUI unchanged for the user.

> **Phase 6 — Organizational Memory subsystem.**
> Promote `memory.py` to `pa-memory`: `DecisionArtifact` store, hybrid retrieval
> (port lexical + add embeddings), `LearningService`, outcome capture. *Deliverable:*
> the learning loop runs on real storage with semantic recall.

> **Phase 7 — Observability + second connector + hardening.**
> OTel spans across sync + decision runs, structured logging, connector health
> surface; add a second real connector (e.g. Jira) to prove the framework
> generalizes; config UX (YAML + typed schemas + fail-fast). *Deliverable:*
> production-posture platform with two connectors and full tracing.

**Why this order:** it builds the dependency DAG bottom-up *but* keeps the v1
agent loop runnable the entire time (Phase 0 preserves it; it only changes its
data source in Phase 5). Risk is front-loaded into structure (Phase 0) and the
vocabulary (Phase 1), which are the expensive-to-change decisions. Connectors —
the open-ended, ever-growing part — come *after* the contracts they must satisfy
exist, so the first connector validates the framework instead of defining it.

---

## Appendix — Open decisions that fork the design

These genuinely change the plans and are the user's call (recommendations given):

1. **Evolve-in-place vs greenfield.** *Recommend evolve* (Phase 0 preserves v1).
2. **uv workspace vs single package + import-linter.** *Recommend workspace.*
3. **Storage engine + ORM** (SQLite/SQLAlchemy-async/SQLModel vs alternatives).
   *Recommend SQLite-first via SQLAlchemy 2.0 async + SQLModel, Postgres-ready.*
4. **First reference connector** (simplest-to-validate vs highest-value). *Recommend
   a simple one first (GitHub/CSV) in Phase 4, Jira as the second in Phase 7.*
5. **Roadmap depth now** — full 7 phases vs a thinner spine (Phases 0–5) first.
