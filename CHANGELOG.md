# Changelog

All notable changes to ProductAgents are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

The history splits into two arcs. **V1** built the advisory decision pipeline
end-to-end in a Textual TUI — evidence → five analysts → debate → strategist →
judge → risk → governance → human approval, with append-only persistence and an
outcome-learning loop. **V2** then re-architected that slice in place (no
rewrite) into a product-decision platform: a six-package `uv` workspace, a
canonical data layer, durable SQL storage, knowledge services, live connectors,
a DB-backed organizational memory, and connector observability.

## [Unreleased]

### Added
- **Decision tracing** — every run is wrapped in a `decision.run` span and each graph node in a `decision.<node>` span (the `span()` shim moved to `pa-core` for shared use). (#49)
- **Headless / scheduled sync** — a `productagents sync` subcommand runs a one-shot connector sync for cron/launchd (non-zero exit on failure), and an optional in-process scheduler auto-syncs on the `PRODUCTAGENTS_SYNC_INTERVAL` cadence while the app runs. (#49)

### Changed
- **Required CI gate on `main`** — branch protection now requires the test, typecheck, and security jobs to pass. (#49)
- **Documentation reconciled with the V2 platform** — the README no longer frames the code as a "thin slice", the Technology Stack reflects the real persistence / connector / observability stack, the two live connectors (GitHub, Jira) are named, headless sync + connector health are documented, and this CHANGELOG was added and linked.

### Internal
- **Post-V2 code-quality pass** — a typed `stream_events` module is now the single source of truth for the progress wire format (the runner warns on unknown chunks instead of dropping them silently); `tui/app.py` was split into `_constants.py` + a `PanelIndicator` state/spinner machine; the TUI uses the public `get_css_variables()` API. (#48)

## [2.0.0] — 2026-06-27 — V2: the product-decision platform

Re-architected the V1 slice into a six-package `uv` workspace (`pa-core`,
`pa-agents`, `pa-app`, `pa-memory`, `pa-knowledge`, `pa-connectors`) under the
`productagents` namespace, with a canonical data layer, durable storage,
knowledge services, live connectors, a DB-backed organizational memory, and
connector observability — evolve-in-place, no rewrite.

### Added
- **Workspace boundaries (Phase 0)** — scaffolded the six member packages and moved schemas/config/logging into `pa-core`, the graph/nodes/runner into `pa-agents`, memory into `pa-memory`, and setup/TUI into `pa-app`; the legacy `src/` tree was removed. `import-linter` contracts now enforce the layer DAG and ban `requests` platform-wide. ADR-0001 records the decision. (#37)
- **Canonical models (Phase 1)** — a shared enum vocabulary, branded typed identifiers, `SourceRef`/`ExternalRef` lineage, and a `CanonicalModel` base with a fingerprint helper, plus bounded-context model modules: discovery, planning (a unified `Initiative`), strategy (`Objective`, `KeyResult`), and measurement (`ProductMetric`, `MetricSnapshot`). V1 decision models migrated into `models/decision.py`; `schemas.py` was deleted and all imports moved to the `core.models` re-export surface, guarded by a round-trip / no-leakage mapper harness. (#38)
- **Canonical storage (Phase 2)** — an async engine + config, canonical-model ↔ row mapping, a `Repository` protocol with a generic `CanonicalRepository`, a `CanonicalSink` write boundary with `DbCanonicalSink`, and an Alembic project with the initial `canonical_record` migration. Re-syncs preserve `ingested_at`. (#39)
- **Knowledge services (Phase 3)** — a `Page[T]` pagination result, a `Query[T]` base over a `CanonicalQueryService` engine, and `FeedbackService` / `InitiativeService` / `MetricsService` behind a `KnowledgeServices` container with `build_services`. (#40)
- **Connector framework (Phase 4)** — a `Connector` ABC with value types and a `FakeSink`, a shared async httpx client with transient retry, entry-point connector discovery, and a concurrent degrade-don't-crash sync runtime. First connector: GitHub issues → `CustomerFeedback`, with a paginated `since`-cursor client and an end-to-end test (sync → store → `FeedbackService`). (#42)
- **Connector wiring (Phase 7a)** — a YAML config loader (`connectors.yaml`, or `PRODUCTAGENTS_CONNECTORS_FILE`) with typed, fail-fast validation surfaced on the home menu; `run_connector_sync` syncs into the canonical store and persists per-connector cursors via a new `sync_state` table + `SyncStateStore`; a **Sync data sources** home action and connector readiness line. Malformed config degrades instead of crashing the TUI. (#45)
- **Jira connector (Phase 7b)** — a second connector (pure issue → `CustomerFeedback` mapper, JQL-building client with token pagination, Basic-auth `JiraConnector` with health + incremental sync) added purely through the `config_cls` + entry-point seams, proving zero app changes. Uses Jira's enhanced-search endpoint with a UTC-safe JQL `since` buffer. (#46)
- **Connector observability (Phase 7c)** — an httpx-aware failure classifier (`connector_errors.py`), an `observability.span()` span-like structured logger (no OpenTelemetry dependency), per-sync spans with classified escaped failures, GitHub + Jira surfacing classified error messages, a `check_connector_health()` probe, and a **Check connector health** home-menu button. (#47)

### Changed
- **Agents rewired onto dependency injection (Phase 5)** — nodes receive an `AgentContext` (model + `FeedbackReader` / knowledge-service slices) instead of a bare model; `run_analyst` and the analyst nodes were refactored to consume it. Customer Research now reads live store `CustomerFeedback`, falling back to scenario evidence when the store is empty. A per-run `AgentContext` session boundary opens the DB at the app edge, keeping nodes engine-free, and an `agents→services` storage boundary is enforced. `build_graph` still accepts a bare model for tests. (#43)
- **Organizational memory moved to the database (Phase 6)** — `memory.py` was split into a package; `pa-memory` gained a SQLAlchemy schema (decision + outcome tables), a `DecisionStore` that persists/reads full records, an `Embedder` protocol with a deterministic `HashingEmbedder`, and hybrid retrieval (cosine `semantic_matches` + `also_relevant`). A `LearningService` is the read/write face; the `recall` node reads lessons through `AgentContext.learning`, and the TUI records/recalls via DB-backed seams. The DB is the system of record; JSONL is export/audit only. `pa-memory` owns its own Alembic project. (#44)

### Fixed
- Resolved all pre-commit `ty` diagnostics across the test suite so the type-check hook passes clean (typed `query_one` calls, guarded `Optional` fields, literal verdict params). (#41)
- `disable_existing_loggers=False` in the Alembic `fileConfig` to prevent a test-isolation regression; `md5(..., usedforsecurity=False)` to satisfy bandit B324. (#39, #44)

## [1.0.0] — 2026-06-23 — V1: the advisory decision pipeline

The full evidence → analysts → debate → strategist → judge → risk → governance →
human-approval pipeline, assembled as a LangGraph `StateGraph`, running live in a
Textual TUI and persisting every decision. Nodes degrade rather than crash, and
the whole suite runs offline against a fake model.

### Added — the pipeline
- **Thin end-to-end slice** — typed schemas (initiatives, evidence, reports, decisions), an evidence loader with a bundled `sample` scenario, a provider-agnostic model factory, the first two analyst nodes (Customer Research, Product Analytics), the strategist, a normalized streaming runner over the graph, a Textual TUI entry point, and an append-only decision log. (#1)
- **Structured debate** — an advocate/skeptic debate node looping `PRODUCTAGENTS_DEBATE_ROUNDS` (each round = one advocate argument + one skeptic rebuttal), with the full transcript fed into the strategist, streamed live, and recorded on the `DecisionRecord`. (#3)
- **Full analyst team** — added Market, Business, and Technical analysts and their evidence sources, so five analysts now run in parallel from `START`. (#10)
- **Risk evaluation** — a Risk Team node with five specialized reviewers (delivery, adoption, strategic, financial, organizational), streamed live and persisted. (#7)
- **Governance approval** — a Product Portfolio Manager node producing an advisory verdict, routed the recommendation + risks, streamed and recorded. (#8)
- **Human-in-the-loop governance** — a `human_approval` node added via an opt-in `human_in_the_loop` flag on `build_graph` (compiled with an `InMemorySaver` checkpointer); on a governance interrupt the runner surfaces it, the TUI shows an approval modal, and the human's approve/reject/request-analysis choice resumes the graph as the binding `FinalVerdictEvent`. (#13)
- **LLM-as-Judge quality gate** — `JudgeFinding`/`JudgeVerdict` schemas and a judge node between strategist and risk that scores evidence grounding + rationale coherence against `PRODUCTAGENTS_JUDGE_THRESHOLD`; on a failing, retryable verdict it injects its critique and loops back to the strategist up to `PRODUCTAGENTS_JUDGE_MAX_RETRIES` times. Surfaced as `JudgmentEvent` and rendered in a TUI panel. (#24)

### Added — evidence & learning
- **Pluggable evidence** — `EvidenceSourceRef` provenance schemas, an `EvidenceSource` protocol with `ScenarioSource` and `DirectorySource`, and a `collect_evidence` resolver (scenario name → directory path → bundled `sample`). The TUI picks the source per run, shows provenance, and persists it on the record. (#15)
- **Outcome learning — capture** — reflection/outcome schemas with a stable `decision_id`, an append-only `outcomes.jsonl` log, and a reflection agent (Ctrl+R in the TUI) that compares predicted vs actual outcomes and records a prediction-accuracy score + lessons. (#9)
- **Outcome learning — injection** — lexical lesson-retrieval over past decisions and a `recall` node that selects relevant lessons and injects them into the strategist prompt, emitted as a runner event, rendered in the TUI, and persisted. (#12)
- **Derived past-decision lessons** — synthesize prediction-style lessons from similar past decisions (validated-first ranking, dedup by title) when explicit reflections are sparse. (#35)

### Added — configuration & onboarding
- **`.env`-based configuration** — a dotenv-backed config loader, `.env` loaded automatically at the entry point (shell vars take precedence), and a `.env.example` template. (#16)
- **First-run setup wizard** — a `HomeScreen` landing menu with config status, a static config-readiness check + provider registry, and a `SetupScreen` (16-provider dropdown) that writes model/provider/key to `.env` and rebuilds the model without a restart. (#18)
- **OpenRouter free-model support** — a `langchain-openrouter` dependency, an `openrouter:`-prefixed default free model (the `:free` suffix is preserved), and docs on the tool-calling requirement. (#25)

### Added — TUI & live feedback
- **Architecture diagrams** added to the README (general architecture, six layers, agent architecture). (#26)
- **Three-lane TUI with error surfacing** — an analyst grid, a Status/Errors panel with failed-panel badges, `NodeErrorEvent` for analyst/debate/risk/strategist/governance failures, and per-stage themed accents. (#20)
- **Live state indicators** — waiting state for downstream panels, an animated running spinner, warning on judge-fail / non-approve verdicts, and panel handoff (waiting → running → done). (#29)
- **Live strategist recommendation** — `RecommendationEvent` renders the recommendation as soon as a node produces it, not only at run end. (#34)
- **Decision-console redesign** — a situation-room palette with idle-recede tokens, a pipeline-rail spine tracing the decision through stages, a labelled/autofocused initiative input, result-panel emphasis, a quiet status strip, unified modal/menu identity, and testable `_format` render helpers. (#36)

### Changed — resilience
- **Transient-error retry** — `get_model()` retries transient provider errors (e.g. free-tier 429/5xx) with backoff up to `PRODUCTAGENTS_MAX_RETRIES` (default 6); the strategist sets a `failed` flag on degrade, the graph fails fast to `END` when no recommendation can be produced, and a `DegradedRunScreen` offers retry/decide/quit (failed runs are never auto-recorded). (#30)
- **File-based logging + structured-output chokepoint** — `configure_logging()` writes to a rotating file only (`PRODUCTAGENTS_LOG_FILE` / `PRODUCTAGENTS_LOG_LEVEL`, since the TUI owns the terminal); all LLM-calling nodes route through an `invoke_structured()` wrapper that turns a `None` structured result into a clear `StructuredOutputError` and logs it. (#31)
- **Provider error classification + fail-fast** — a provider-agnostic error classifier (no SDK import) marks rate-limit / auth / tool-calling-unsupported as fatal at the structured-call chokepoint; fatal errors abort early via `RunAbortedEvent` and a friendly TUI banner, while transient errors keep degrading per-node. (#32)
- **Non-Anthropic providers** — decision runs work across providers and degrade gracefully on bad records. (#19)
- Right-lane TUI panels stay on-screen with long content. (#33)

### Internal
- **CI & security** — GitHub Actions split into parallel test / typecheck / security jobs (pip-audit, bandit, gitleaks) with Dependabot for uv + github-actions; `import-linter` layer contracts; ruff (explicit ruleset) + the `ty` type checker with pre-commit hooks. (#5, #6, #21)
- **Coverage floor** — pytest-cov with a 90% coverage floor. (#2)
- **De-duplication pass** — shared `format_initiative` / `format_recommendation` prompt builders, a single `run_analyst` executor for the five analysts, centralized `env_int`/`env_float` parsing, deduped JSONL read/write, dispatch-table-driven runner + TUI event handling, and per-directory `CLAUDE.md` docs. (#17, #28)

[Unreleased]: https://github.com/mcapanema/ProductAgents/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/mcapanema/ProductAgents/releases/tag/v2.0.0
[1.0.0]: https://github.com/mcapanema/ProductAgents/releases/tag/v1.0.0
