# ADR-0001: uv Workspace and Layer Boundaries

**Date:** 2026-06-23
**Status:** Accepted

## Context

ProductAgents v2 targets a six-layer product-decision OS. Phase 0 must enforce
those layer boundaries structurally before any new code is written, so that the
"evolve in place" constraint holds: behaviour is unchanged, but the import graph
is locked down.

## Decision

Adopt a **uv workspace** with six member packages sharing a single
`productagents` namespace (PEP 420 implicit namespace package — no `__init__.py`
at the `productagents/` root):

| Package | Namespace | Role |
|---|---|---|
| `pa-core` | `productagents.core` | Pydantic schemas, config, logging — no heavy deps |
| `pa-agents` | `productagents.agents` | LangGraph nodes, LLM factory, graph, runner |
| `pa-memory` | `productagents.memory` | Append-only JSONL decision/outcome store |
| `pa-knowledge` | `productagents.knowledge` | Stub — retrieval layer (v2 roadmap) |
| `pa-connectors` | `productagents.connectors` | Stub — external integrations (v2 roadmap) |
| `pa-app` | `productagents.app` | Textual TUI, setup wizard |

An umbrella `pyproject.toml` at the workspace root lists all six as dependencies
and declares the `productagents` entry point (`app.tui.app:main`), but ships no
importable code of its own (`bypass-selection = true`).

**Layer DAG** (higher may import lower, never the reverse) enforced by
[import-linter](https://import-linter.readthedocs.io/) contracts in
`pyproject.toml`:

1. **Layered architecture** — `app` > `agents` > (`knowledge` | `memory`) > `core`
2. **Connectors are isolated** — `app`, `agents`, `knowledge` must not import
   `productagents.connectors` directly.
3. **Core has no heavy dependencies** — `core` must not import `httpx`, `requests`,
   `langchain`, `langgraph`, `sqlalchemy`, or `textual`.
4. **No requests anywhere** — `requests` is banned platform-wide; use `httpx`.

Contracts are verified with `uv run lint-imports` (CI gate, 4 kept, 0 broken).

## Alternatives Rejected

**Single package + import-linter only** — Keeps the flat `src/productagents/`
layout and uses import-linter contracts alone to express boundaries. Rejected
because the boundaries are soft (a developer can bypass them by ignoring the CI
gate); a workspace with separate `pyproject.toml` files makes the isolation
structural — a package literally cannot import a peer it doesn't declare.

**Polyrepo** — Separate git repositories per layer. Rejected because the team
size and current slice don't justify the coordination overhead, and `uv
workspaces` give the same hard-boundary benefit within a single repo with a
single lock file and a single `uv sync`.

## Consequences

- `uv sync` resolves all six members together from one lock file.
- All tests remain in a single `tests/` tree (no per-package test dirs); imports
  use the new namespace paths (`productagents.core.schemas`, etc.).
- `[tool.coverage.paths]` in the root `pyproject.toml` maps each member's
  `src/productagents/` tree back to the `productagents` namespace so coverage
  spans all packages without duplication.
- Empty stub packages (`pa-knowledge`, `pa-connectors`) are omitted from
  coverage reporting to avoid dragging the percentage down.
- Adding a new layer or promoting a stub to a real package requires: adding a
  `pyproject.toml` under `packages/pa-<name>/`, declaring it in the workspace
  `members`, adding it as a workspace dependency in the umbrella, and wiring an
  import-linter contract for its position in the DAG.
