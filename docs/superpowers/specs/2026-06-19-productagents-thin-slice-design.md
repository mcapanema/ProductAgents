# ProductAgents — Thin End-to-End Slice Design

**Status:** Approved (design)
**Date:** 2026-06-19
**Author:** Murilo Capanema (with Claude)

## Purpose

ProductAgents is a multi-agent framework for product decision-making under
uncertainty (see `README.md` for the full vision: 7-stage architecture, ~15
agent roles, organizational memory). This spec covers **only the first
milestone**: a thin, working end-to-end slice that proves the core pipeline —
evidence → parallel analysts → strategist recommendation — rendered live in a
TUI. Debate, the full analyst/risk teams, governance, and the reflection loop
are explicitly deferred to later iterations.

The slice exists to validate the spine (LangGraph orchestration, provider-
agnostic LLM access, typed agent outputs, mock-evidence loading, and a Textual
UI consuming streamed graph execution) before adding breadth.

## Scope

### In scope (this slice)

- UV-based Python 3.14 project scaffolding and package layout.
- Provider-agnostic LLM access through LangChain `init_chat_model`, selected by
  config/env.
- A LangGraph `StateGraph` with two analyst nodes running in parallel and a
  strategist node fanning in.
- Two analysts only: **Customer Research Analyst** and **Product Analytics
  Analyst**.
- **Product Strategist** producing a typed `Recommendation`.
- Strongly typed (Pydantic v2) schemas for all agent inputs/outputs.
- Mock evidence loaded from local files organized as named "scenarios."
- A Textual TUI that takes an initiative + scenario, shows live analyst
  progress, and renders the final recommendation and analyst reports.
- A lightweight organizational-memory stub: append each `DecisionRecord` to a
  local `decisions.jsonl`.
- Unit + integration tests with a fake chat model (no network).

### Out of scope (later iterations)

- The advocate/skeptic **debate** layer (structured disagreement).
- The remaining analysts (Market, Business, Technical).
- The **Risk Team** (5 reviewers) and **Portfolio Manager** governance.
- The **reflection / outcome-learning** loop (`actual_outcomes`,
  `prediction_accuracy`, `lessons_learned`). The slice records decisions but
  does not evaluate them.
- Real external integrations (CRM, analytics, support, market intelligence).
- LangGraph checkpointing/resume.
- Multi-provider switching UI (the seam exists; only config-level selection).

## Decisions (locked)

| Area | Decision |
|------|----------|
| First milestone | Thin end-to-end slice (not scaffolding-only, not full architecture) |
| Orchestration | LangGraph from the start (`StateGraph`, async streaming) |
| LLM access | Provider-agnostic via LangChain `init_chat_model`, chosen by config/env |
| TUI | Textual |
| Evidence | Local mock files, organized as named scenarios |
| Analysts in slice | Customer Research + Product Analytics |
| Decision memory | Append-only `decisions.jsonl`; **no** reflection/outcome loop |
| Debate | Excluded from slice; enters with the advocate/skeptic layer next |
| Runtime | Python 3.14, UV (not Conda — overrides README) |

## Architecture

```text
Textual App (UI)
   │  user enters initiative, picks evidence scenario
   ▼
LangGraph StateGraph  ── async stream (updates + custom) ──▶  UI widgets (live)
   START
     ├─▶ customer_research_analyst ┐  (parallel fan-out)
     └─▶ product_analytics_analyst ┘
              ▼ (fan-in)
        product_strategist
              ▼
            END  →  DecisionRecord appended to decisions.jsonl
```

### TUI ↔ graph integration

A Textual worker runs `graph.astream(state, stream_mode=["updates", "custom"])`
and forwards each chunk as a Textual message to the widgets. Analyst nodes emit
progress through `get_stream_writer()` (e.g. "reading evidence…", "drafting
findings…"); `updates` chunks carry committed node state. This keeps the UI
responsive and tied to real graph state.

Rejected alternatives: (a) run to completion then render once — no live
progress, defeats the TUI; (b) callback/polling bridge — redundant given native
streaming.

## Components & File Structure

- `src/productagents/llm.py` — provider-agnostic model factory wrapping
  `init_chat_model`, selected by env (`PRODUCTAGENTS_MODEL`, optional
  `PRODUCTAGENTS_MODEL_PROVIDER`). Single seam for all providers.
- `src/productagents/schemas.py` — Pydantic v2 models: `Initiative`,
  `Evidence`, `AnalystReport`, `Recommendation`, `DecisionRecord`.
- `src/productagents/evidence.py` — loads a named scenario's mock evidence
  files into an `Evidence` object; typed errors on missing/malformed input.
- `src/productagents/agents/customer_research.py` — analyst node function.
- `src/productagents/agents/product_analytics.py` — analyst node function.
- `src/productagents/agents/strategist.py` — strategist node function.
- `src/productagents/graph.py` — `StateGraph`, the graph state schema (analyst
  reports accumulate via a reducer), graph compilation.
- `src/productagents/memory.py` — appends a `DecisionRecord` to
  `decisions.jsonl`.
- `src/productagents/tui/app.py` (+ widget modules) — Textual app: input
  screen, live analyst panels, strategist result view.
- `data/scenarios/<name>/` — bundled mock evidence (customer feedback `.md`,
  analytics `.json`). At least one scenario shipped.
- `tests/` — per-node unit tests (fake model), graph integration test, schema
  round-trips, evidence-loader tests.

### Graph state (shape)

State carries the `Initiative`, the loaded `Evidence`, a list of
`AnalystReport` that accumulates across the two parallel analyst nodes (via a
list-append reducer), and the final `Recommendation`. Exact field names and
signatures are defined in the implementation plan.

### Schemas (intent; exact fields finalized in the plan)

- `Initiative` — the proposal under evaluation (title, description).
- `Evidence` — scenario name plus the loaded customer-feedback and analytics
  payloads.
- `AnalystReport` — analyst id/role, findings, supporting signals, and a
  `failed: bool` flag for degraded output.
- `Recommendation` — recommendation text, `confidence` (0.0–1.0), rationale,
  expected outcomes.
- `DecisionRecord` — initiative + recommendation + timestamp, serialized to
  `decisions.jsonl`.

## Data Flow

1. User enters an initiative and selects a scenario in the TUI.
2. Evidence loader reads the scenario files into an `Evidence` object (errors
   surfaced before the graph runs).
3. Graph invoked with `Initiative` + `Evidence` in state.
4. Both analysts run in parallel; each emits progress (`custom`) and returns a
   typed `AnalystReport` (committed via `updates`).
5. Strategist consumes the initiative + both reports and returns a typed
   `Recommendation`.
6. A `DecisionRecord` is appended to `decisions.jsonl`.
7. The TUI renders the recommendation alongside both analyst reports.

## Error Handling

- **LLM / structured-output failure in a node:** caught locally; node emits a
  `custom` error event and returns a degraded `AnalystReport` with
  `failed=True`. The strategist notes the missing input rather than crashing.
  The UI shows that analyst's panel in an error state.
- **Missing/malformed evidence files:** evidence loader raises a typed error,
  caught at startup and surfaced in the TUI before the graph runs.
- **Missing API key / model config:** validated at launch with a clear,
  actionable message.

## Testing Strategy

Test-driven throughout. Core logic lives in non-UI modules so it is unit
testable.

- **Node unit tests:** each analyst and the strategist tested with a fake/stub
  chat model returning canned structured output — deterministic, no network.
- **Graph integration test:** asserts the two analysts fan out in parallel and
  that the strategist receives both reports; uses a fake model.
- **Schema tests:** round-trip validation and the `confidence` 0.0–1.0 bound.
- **Evidence loader tests:** against a fixture scenario, including the
  missing/malformed error paths.
- **TUI:** kept thin; minimal logic, exercised lightly. The slice's
  correctness lives in the testable core.

## Technology Stack (pinned)

- Python 3.14, UV (package/dependency management; overrides README's Conda).
- LangGraph + LangChain (`init_chat_model`) for orchestration and provider-
  agnostic model access.
- Pydantic v2 for typed schemas / structured outputs.
- Textual for the TUI.
- pytest for tests.
- One bundled mock evidence scenario.

## Success Criteria

- `uv run` launches the TUI; the user enters an initiative, picks the bundled
  scenario, and watches both analysts run in parallel with live progress.
- A typed `Recommendation` (with confidence and rationale) renders, and a
  `DecisionRecord` is appended to `decisions.jsonl`.
- The full test suite passes offline using the fake chat model.
- Switching the configured model/provider requires only an env/config change,
  no code changes to agents.

## Follow-on Iterations (not this spec)

1. Advocate/Skeptic **debate** layer feeding the strategist.
2. Remaining analysts (Market, Business, Technical).
3. **Risk Team** + **Portfolio Manager** governance.
4. **Reflection / outcome-learning** loop over `decisions.jsonl`.
5. Real evidence integrations; LangGraph checkpointing/resume.

Each follow-on gets its own spec → plan → implementation cycle.
