# Changelog

All notable changes to ProductAgents are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

The history splits into two arcs: **V1** — building the advisory decision
pipeline end-to-end in the Textual TUI — and **V2** — re-architecting that slice
(evolve-in-place) into a product-decision platform with a canonical data layer,
durable storage, knowledge services, live connectors, a DB-backed organizational
memory, and connector observability.

## [Unreleased]

### Added
- CI is now a required gate on `main` (test / typecheck / security); every decision run emits structured `decision.run` / `decision.<node>` spans; a headless `productagents sync` command plus a `PRODUCTAGENTS_SYNC_INTERVAL` scheduler keep connector data fresh outside the TUI. (#49)

### Changed
- Documentation reconciled with the V2 platform: the README no longer frames the code as a "thin slice", the Technology Stack reflects the real persistence / connector / observability stack, and this CHANGELOG was added and linked.

### Internal
- Post-V2 code-quality pass: typed stream-event protocol, `tui/app.py` split (PanelIndicator / constants), public CSS API. (#48)

## [2.0.0] — 2026-06-27 — V2: the product-decision platform

Re-architected the V1 slice into a six-package `uv` workspace with a canonical
data layer, durable storage, knowledge services, live connectors, a DB-backed
organizational memory, and connector observability — without a rewrite
(evolve-in-place).

### Added
- **Workspace boundaries** — split into six member packages (`pa-core`, `pa-agents`, `pa-app`, `pa-memory`, `pa-knowledge`, `pa-connectors`) under the `productagents` namespace, governed by import-linter layer contracts. (#37)
- **Canonical models** — bounded-context Pydantic models (discovery / planning / strategy / measurement / decision) on a shared `CanonicalModel` base with branded ids and source-ref lineage. (#38)
- **Canonical storage** — a `CanonicalRecord` table, generic `CanonicalRepository[T]`, `DbCanonicalSink`, and Alembic migrations over SQLite/Postgres. (#39)
- **Knowledge services** — a paged `Query[T]` engine plus `FeedbackService` / `InitiativeService` / `MetricsService` behind a `KnowledgeServices` container. (#40)
- **Connector framework** — pluggable httpx-based connectors that sync external records into the canonical store *before* a run; first connector: GitHub issues → `CustomerFeedback`. (#42)
- **Connector wiring** — YAML connector config (`connectors.yaml`), fail-fast typed validation surfaced on the home menu, a "Sync data sources" action, and persisted per-connector cursors. (#45)
- **Jira connector** — a second connector added purely through config / entry-point seams, with zero app changes. (#46)
- **Connector observability** — an httpx-aware error classifier, span-style structured logs, and a "Check connector health" home action. (#47)

### Changed
- **Agents rewired onto dependency injection** — nodes now receive an `AgentContext` (model + knowledge-service slices); Customer Research reads synced `CustomerFeedback`, degrading to scenario evidence when the store is empty. (#43)
- **Organizational memory moved to the database** — `pa-memory` became a DB-backed store with hybrid (lexical + semantic) lesson retrieval and a `LearningService`; the `recall` node reads lessons through `ctx.learning`. The DB is the system of record; JSONL is export/audit only. (#44)

### Fixed
- Resolved all pre-commit `ty` diagnostics so the type-check hook passes clean. (#41)

## [1.0.0] — 2026-06-23 — V1: the advisory decision pipeline

The full evidence → analysts → debate → strategist → judge → risk → governance →
human-approval pipeline, running live in a Textual TUI and persisting every
decision.

### Added
- **Thin end-to-end slice** — evidence loader, the first analysts, strategist, a normalized streaming runner, the Textual TUI, and an append-only decision log. (#1)
- **Structured debate** — an advocate/skeptic debate node with configurable rounds, streamed live and recorded on the decision. (#3)
- **Risk evaluation** — a five-reviewer Risk Team (delivery / adoption / strategic / financial / organizational). (#7)
- **Governance approval** — the Product Portfolio Manager advisory verdict. (#8)
- **Outcome learning (capture)** — reflection mode that compares predicted vs actual outcomes and records lessons. (#9)
- **Full analyst team** — added Market, Business, and Technical analysts (five parallel analysts). (#10)
- **Outcome learning (injection)** — a `recall` node that retrieves past-decision lessons and injects them into the strategist prompt. (#12)
- **Human-in-the-loop governance** — a `human_approval` node (LangGraph interrupt) + approval modal; the human makes the binding call. (#13)
- **Pluggable evidence** — an `EvidenceSource` protocol, scenario/directory sources, and provenance shown in the TUI and saved on the record. (#15)
- **First-run setup wizard** — a home menu + setup screen that writes model / provider / key to `.env`. (#18)
- **LLM-as-Judge quality gate** — scores the recommendation and loops back to the strategist on a failing verdict. (#24)
- **OpenRouter free-model support** — provider support and a free default model. (#25)
- **Architecture diagrams** and a redesigned decision-console TUI with live state indicators. (#26, #29, #36)

### Changed
- `.env`-based configuration loaded automatically on startup. (#16)
- Provider errors classified into fatal (rate-limit / auth / no-tool-calling) vs transient; transient errors retried with backoff (`PRODUCTAGENTS_MAX_RETRIES`), fatal errors fail fast with one banner. (#30, #31, #32)
- Deduplicated the five analysts onto a shared executor and added per-directory `CLAUDE.md` docs. (#17)

### Internal
- GitHub Actions CI split into parallel test / typecheck / security jobs (pip-audit, bandit, gitleaks, Dependabot); import-linter layer contracts; ruff + ty. (#5, #6, #21)

[Unreleased]: https://github.com/mcapanema/ProductAgents/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/mcapanema/ProductAgents/releases/tag/v2.0.0
[1.0.0]: https://github.com/mcapanema/ProductAgents/releases/tag/v1.0.0
