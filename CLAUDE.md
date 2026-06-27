# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ProductAgents is a multi-agent framework for product decision-making under uncertainty. The README describes a target seven-stage / six-layer architecture, but the repository currently implements a **thin end-to-end slice** of it. Keep that distinction in mind: the README is the vision; the code is the slice. The implemented slice is:

```
evidence → [customer_research ∥ product_analytics ∥ market ∥ business ∥ technical] → debate (advocate vs skeptic) ┐
                                                                  recall (past lessons) ┴→ strategist → judge → risk → governance (advisory) → human_approval → DecisionStore (DB)
```

Everything runs live in a Textual TUI.

## Directory structure

The codebase is a **uv workspace** with six member packages sharing the
`productagents` namespace (PEP 420 namespace package — no `__init__.py` at the
`productagents/` level):

```
pyproject.toml              # workspace root + umbrella (no importable code)
packages/
├── pa-core/                # productagents.core.*  — canonical models, config, logging
│   └── src/productagents/core/
│       ├── models/         #   canonical models by bounded context (see core/CLAUDE.md)
│       │   ├── _base.py · discovery.py · planning.py · strategy.py
│       │   ├── measurement.py · decision.py   # decision.py = migrated v1 schemas
│       │   └── __init__.py #   public re-export surface (import from here)
│       ├── enums.py        #   shared Literal vocabularies
│       ├── ids.py          #   branded NewType identifiers
│       ├── refs.py         #   SourceRef / ExternalRef lineage
│       ├── config.py       #   env-var settings (PRODUCTAGENTS_* vars)
│       └── logging_config.py
├── pa-agents/              # productagents.agents.*  — graph nodes + orchestration
│   └── src/productagents/agents/
│       ├── _analyst.py     #   shared run_analyst() executor for the 5 analysts
│       ├── _format.py      #   shared prompt formatters
│       ├── _stream.py      #   get_writer() progress-event helper
│       ├── _llm_call.py    #   invoke_structured() chokepoint (logging + retry)
│       ├── context.py      #   AgentContext DI container (model + knowledge service slices)
│       ├── llm.py          #   get_model() — the only provider-agnostic factory
│       ├── llm_errors.py   #   error classifier (fatal vs transient)
│       ├── evidence.py     #   EvidenceSource protocol + scenario/dir sources
│       ├── graph.py        #   LangGraph StateGraph assembly + GraphState
│       ├── runner.py       #   graph→UI boundary: normalizes stream into events
│       ├── customer_research.py · product_analytics.py · market.py
│       ├── business.py · technical.py            # the five parallel analysts
│       ├── recall.py · strategist.py · judge.py · risk.py · governance.py
│       ├── human_approval.py # HITL interrupt node (added only when enabled)
│       ├── reflection.py   #   OUT OF GRAPH: post-hoc outcome reflection
│       └── data/scenarios/<name>/  # bundled mock evidence files
├── pa-app/                 # productagents.app.*  — TUI + setup wizard
│   └── src/productagents/app/
│       ├── setup.py        #   check_config + write_env
│       ├── decision_context.py #   per-run AgentContext session opener (DB + services)
│       └── tui/            #   Textual app + modal screens (see tui/CLAUDE.md)
│           ├── app.py · app.tcss · approval.py · reflection.py
│           ├── home_screen.py · setup_screen.py · degraded.py
│           ├── rail.py     #   PipelineRail spine widget
│           └── _format.py  #   pure Rich-markup render helpers
├── pa-memory/              # productagents.memory  — organizational-memory subsystem (DB store + hybrid retrieval + LearningService)
│   └── src/productagents/memory/     # store.py · tables.py · retrieval.py · service.py · embedding.py · jsonl.py (export/audit)
├── pa-knowledge/           # productagents.knowledge.*  — stub, ready for v2
│   └── src/productagents/knowledge/__init__.py
└── pa-connectors/          # productagents.connectors.*  — Layer-1 connector framework
    └── src/productagents/connectors/
        ├── base.py · http.py · registry.py · runtime.py  # the framework
        ├── connector_errors.py · observability.py        # error classifier + span logger
        └── github/         #   first connector: issues → CustomerFeedback
tests/                      # offline suite, FakeChatModel (see tests/CLAUDE.md)
docs/design/adr/            # Architecture Decision Records
```

**Import path examples:**
```python
from productagents.core.models import DecisionRecord, Recommendation, Initiative
from productagents.core.models import CustomerFeedback, Feature, ProductMetric
from productagents.core.config import settings
from productagents.agents.graph import build_graph
from productagents.agents.runner import run_decision
from productagents.agents.evidence import collect_evidence
from productagents.app.setup import check_config
from productagents.app.tui.app import main
import productagents.memory as memory
```

Each key sub-directory has its own `CLAUDE.md` with the local contract.

## Commands

This project uses **uv** (not Conda, despite the README's "Technology Stack" note). Requires Python ≥ 3.14.

```bash
uv sync                 # install deps + all workspace members (incl. dev group)
uv run productagents    # launch the TUI
uv run pytest           # full suite — runs offline with a fake model, no API key
uv run pytest tests/test_debate.py                         # one file
uv run pytest tests/test_debate.py::test_name -x           # one test
uv run lint-imports     # verify 6 import-linter layer contracts (layers + forbidden)
uv run ruff check packages tests  # lint all source and test trees
uv run ty check         # type check (pyright-based)
```

`uv sync` resolves all six workspace members (`packages/*`) together. `pytest` auto-runs coverage (`--cov`, configured in `pyproject.toml`) and writes `htmlcov/`. `[tool.coverage.paths]` maps each member's `src/productagents/` tree back to the namespace so coverage spans all packages. `asyncio_mode = "auto"`, so `async def test_*` functions need no decorator.

### Runtime configuration (env vars)

- `PRODUCTAGENTS_MODEL` — provider-prefixed model id, default `anthropic:claude-sonnet-4-6`. For non-LangChain-native providers also set `PRODUCTAGENTS_MODEL_PROVIDER`. Provide the matching key (e.g. `ANTHROPIC_API_KEY`).
- `PRODUCTAGENTS_DEBATE_ROUNDS` — debate rounds, default 2 (each round = one advocate argument + one skeptic rebuttal).
- `PRODUCTAGENTS_JUDGE_THRESHOLD` — judge pass threshold for both rubric dimensions (evidence grounding, rationale coherence), default 0.7.
- `PRODUCTAGENTS_JUDGE_MAX_RETRIES` — max strategist revisions the judge can trigger, default 1. `0` makes the judge score-only (it never loops back to the strategist).
- `PRODUCTAGENTS_MAX_RETRIES` — automatic retry budget (with backoff) for transient provider errors (e.g. free-tier OpenRouter 429/5xx), default 6.
- `PRODUCTAGENTS_LOG_FILE` — path of the rotating log file (default `productagents.log`). Logging is **file-only**: the Textual TUI owns the terminal, so nothing is written to stdout/stderr.
- `PRODUCTAGENTS_LOG_LEVEL` — `DEBUG`/`INFO`/`WARNING`/`ERROR` (default `INFO`; invalid values fall back to `INFO`). `DEBUG` logs every structured LLM call; failures (including a model that returns no structured output) are logged at `ERROR` with a full traceback.

> **Structured output requires tool/function calling.** Every node calls
> `model.with_structured_output(...)`. A model that does not support tool calling
> (e.g. Gemma on OpenRouter) returns no structured object; the run degrades and
> logs a `StructuredOutputError` ("the configured model likely does not support
> tool/function calling"). Pick a tool-capable model — e.g.
> `openrouter:deepseek/deepseek-chat-v3-0324:free`.
>
> Provider failures are now classified (`llm_errors.py`): rate-limit, auth, and
> tool-calling-unsupported are **fatal** and stop the run early with one friendly
> banner (a `RunAbortedEvent`); transient upstream 5xx errors degrade per-node as
> before.

On launch the TUI shows a **home menu** (Set up / Run a decision / Quit) and runs
a **static readiness check** (`setup.check_config`): it derives the provider from
`PRODUCTAGENTS_MODEL`, looks up the matching API-key env var, and verifies it is
present. If anything is missing it auto-opens a **SetupScreen** that writes the
model/provider/key to `.env` (`setup.write_env`) and rebuilds the model so the
new config takes effect without a restart. The check never makes a network call.

## Architecture

The orchestration is a **LangGraph `StateGraph`** assembled in `graph.py`. `GraphState` is a `TypedDict`; the five analysts run in parallel from `START`, so `reports` is an `Annotated[list, operator.add]` reducer that merges their concurrent writes. All five fan in to `debate`, then `strategist`, `risk`, `governance`, then `END`. The compiled graph takes a chat model by dependency injection — every node is wired with `partial(node, model=model)`. **Nodes never construct their own model**; the model comes from `llm.get_model()` (the single provider-agnostic factory) and is passed down. This is what makes tests able to inject `FakeChatModel`. The model-free `recall` node runs in parallel from `START`, selects lessons from relevant past decisions (read at the UI boundary and seeded into state, like `portfolio`), and fans into `strategist` alongside `debate`, closing the Outcome-Learning loop.

**Data flow / layers:**
- `productagents.core.models` — all Pydantic models, split by bounded context
(`discovery`/`planning`/`strategy`/`measurement` synced canonical models +
`decision` decision-run records); import from the `core.models` package surface. There are two flavours of model: the structured-output schemas an LLM call must return (`AnalystFindings`, `DebateArgument`, `Recommendation`) and the assembled/enriched records nodes build from them (`AnalystReport`, `DebateTurn`, `DecisionRecord`). Nodes call `model.with_structured_output(Schema)`.
- `productagents.agents.evidence` — pluggable Layer-1 evidence collection behind an `EvidenceSource` protocol (`collect() -> Evidence`). `ScenarioSource` reads a named scenario from `agents/data/scenarios/<name>/`; `DirectorySource` reads the same five files from any folder. `collect_evidence(spec)` resolves a user-typed string (known scenario name → `ScenarioSource`; existing directory path → `DirectorySource`; blank → bundled `sample`). Every loaded field records an `EvidenceSourceRef` on `Evidence.sources` (provenance), which the TUI persists on the `DecisionRecord`. `load_scenario(name)` remains as a thin wrapper over `ScenarioSource`.
- `productagents.agents.*` — one graph node per file. The five analysts share a single executor (`_analyst.py::run_analyst`) and
  differ only in their `_prompt`; the strategist issues its own single structured
  call. `debate.py` loops rounds, alternating advocate/skeptic personas, each turn
  seeing the full transcript so far. Shared prompt formatters live in
  `_format.py`. After the strategist, the `judge` node (LLM-as-Judge) scores
  the `Recommendation` on evidence grounding and rationale coherence; a deterministic
  threshold decides pass/fail. On a failing, retryable verdict the graph routes back
  to the strategist (which sees the judge's critique) up to `PRODUCTAGENTS_JUDGE_MAX_RETRIES`
  times, then proceeds to risk regardless.
- `productagents.agents.graph` — wires nodes into the StateGraph. `build_graph(context_or_model, *, human_in_the_loop=False)` accepts an `AgentContext` (in production) or a bare model (in tests wrapped by a context fixture); when `human_in_the_loop=True`, appends a `human_approval` node after `governance` and compiles the graph with an `InMemorySaver` checkpointer so it can `interrupt()` and resume.
- `productagents.agents.runner` — the **boundary between the graph and the UI**. `run_decision()` consumes `graph.astream(stream_mode=["updates", "custom"])` and normalizes raw chunks into plain dataclass events (`ProgressEvent`, `NodeCompleteEvent`, `DebateTurnEvent`, `FinishedEvent`, `FinalVerdictEvent`). On a governance `__interrupt__`, `run_decision` awaits the `approver` callback for a `HumanDecision` and resumes via `Command(resume=...)`. The TUI only ever sees these events — it has no LangGraph knowledge.
- `productagents.app.sync` — connector composition root: loads `connectors.yaml` (typed, fail-fast via `plan_connectors`), builds enabled connectors against a `DbCanonicalSink`, runs `run_sync`, and persists cursors via `SyncStateStore`. The TUI home menu triggers it (`Sync data sources`). It also exposes `check_connector_health()` (probe every enabled connector's `health_check()` with no DB) surfaced by the home menu's **Check connector health** action. `pa-app` is the only package permitted to import `pa-connectors`.
- `productagents.app.tui.app` — Textual app. `main()` is the `productagents` entry point. It runs the graph in a `@work` worker, updates panels per event. On a governance `__interrupt__`, `run_decision` calls `_ask_human`, which pushes the `ApprovalScreen` modal (`tui/approval.py`) via `push_screen_wait` so the human can approve, reject, or request further analysis; the human's choice resumes the graph. `FinalVerdictEvent` then arrives and updates the governance panel. On `FinishedEvent`, appends a `DecisionRecord` via an injected `recorder` (default `memory.record_decision`). The TUI has a second input for the evidence source (scenario name or folder path; blank = bundled `sample`); it resolves evidence per run via `collect_evidence`, renders the resolved provenance in an "Evidence Sources" panel, and writes `evidence_sources` onto the `DecisionRecord`.
- `productagents.memory` — DB-backed organizational-memory subsystem. `DecisionStore` persists `DecisionRecord` and `OutcomeRecord` rows in SQLite/Postgres via an injected async session; `LessonRetriever` combines lexical scoring (`LexicalRetriever`) with cosine similarity over hashing embeddings (`SemanticRetriever`) for hybrid retrieval. `LearningService` is the Knowledge-Layer face: `relevant_lessons(initiative)` → lesson strings injected into the strategist, `record_decision` / `record_outcome` on the write side. JSONL (`jsonl.py`) is export/audit only — the DB is the system of record. The `recall` node retrieves lessons through `AgentContext.learning` (a `LessonReader` slice), keeping agents free of sqlalchemy.
- **Outcome Learning has two halves.** The *injection* half runs inside the graph
  (`recall` → `strategist`): `recall` calls `ctx.learning.relevant_lessons(initiative)` and seeds the lessons into graph state. The *capture* half runs **outside** the graph:
  `agents/reflection.py::reflect()` is triggered from the TUI's reflection screen
  (`ctrl+r`, `tui/reflection.py`), compares a past `DecisionRecord`'s predicted
  outcomes against a free-text note, and calls `ctx.learning.record_outcome` (which
  delegates to `LearningService` → `DecisionStore`). `recall` later reads those
  outcomes back via hybrid retrieval. The reflection agent is the one agent not wired into `graph.py`.

### Conventions that matter

- **Nodes degrade, never crash.** Every node wraps its LLM call in `try/except` and returns a fallback (a `failed=True` report, a placeholder debate turn, or a zero-confidence recommendation) so one failure can't abort the graph.
- **Streaming from nodes** goes through `agents/_stream.get_writer()`, not `langgraph.config.get_stream_writer()` directly. The latter raises `RuntimeError` when called outside an active graph run (e.g. a unit test invoking a node directly), so the helper returns a no-op writer in that case. Use `get_writer()` in any new node. The progress dict itself is built via `agents/stream_events.py` helpers (`emit_status`, `emit_error`, `emit_payload`, `emit_fatal`), the single source of truth for the wire keys the runner parses.
- **Testing is fully offline.** `tests/fakes.py::FakeChatModel` maps a schema class → the instance (or `Exception`) its `with_structured_output(schema).ainvoke()` should return. Test nodes by calling them directly with a `FakeChatModel`; test the graph by building it with one.
- **Nodes receive an `AgentContext`, not just a model.** `build_graph(context)` injects `ctx` into the analysts (so any analyst may reach a Knowledge Service) and `ctx.model` into the LLM-only nodes. The Customer Research analyst reads synced `CustomerFeedback` from the local store via `ctx.feedback`, degrading to the scenario evidence text when the store is empty/unavailable. The per-run DB session is opened at the app boundary (`app/decision_context.py`), keeping nodes engine-free — the same pattern `recall` uses for the decision log.

## Adding a stage

To extend toward the README's full architecture (e.g. the planned Risk Evaluation layer): add the schema(s) to `productagents.core.models`, add a node in `productagents.agents.*` using `get_writer()` and structured output, wire it into `productagents.agents.graph` (and `GraphState`), surface it through `productagents.agents.runner` as a new event, and render it in `productagents.app.tui.app`. Plans for upcoming work live in `docs/superpowers/plans/`.

**Layer rules** (enforced by `uv run lint-imports`):
- `pa-app` may import from `pa-agents`, `pa-memory`, `pa-core` — not from `pa-connectors`.
- `pa-agents` may import from `pa-memory`, `pa-core` — not from `pa-app`.
- `pa-memory` and `pa-knowledge` may import from `pa-core` — not from each other or above.
- `pa-core` is dependency-light: no httpx, langchain, langgraph, sqlalchemy, textual.
- `requests` is banned platform-wide (async-first, use httpx).
