# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ProductAgents is a multi-agent framework for product decision-making under uncertainty. The README describes a target seven-stage / six-layer architecture. The code now implements the **full advisory pipeline** on a real **V2 platform substrate** — canonical models, a durable canonical store, knowledge services, live connectors (GitHub, Jira), a DB-backed organizational memory, and connector observability. Agent prompts are **registry assets** (bundled defaults + per-workspace versioned overrides) rather than hardcoded literals. What remains on the road to the README's full vision is breadth (more evidence connectors and the planned layers), not the core loop. The pipeline is:

```
evidence → [customer_research ∥ product_analytics ∥ market ∥ business ∥ technical] → debate (advocate vs skeptic) ┐
                                                                  recall (past lessons) ┴→ strategist → judge → risk → governance (advisory) → human_approval → DecisionStore (DB)
```

Everything runs live through the CLI and the desktop GUI.

## Directory structure

The codebase is a **uv workspace** with seven member packages sharing the
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
│       ├── prompts.py      #   PromptStore — resolve/render/version prompt templates
│       ├── prompts/defaults/*.txt  # bundled default templates (one per node name)
│       └── data/scenarios/<name>/  # bundled mock evidence files
├── pa-app/                 # productagents.app.*  — CLI + IPC edges; console entry point: productagents.app.cli:main
│   └── src/productagents/app/
│       ├── cli.py          #   CLI client + console entry point (main); no subcommand → prints help
│       └── setup.py        #   check_config + write_env (used by ipc.py)
├── pa-memory/              # productagents.memory  — organizational-memory subsystem (DB store + hybrid retrieval + LearningService) + event_store.py (append-only runtime_session/runtime_event log)
│   └── src/productagents/memory/     # store.py · tables.py · retrieval.py · service.py · embedding.py · jsonl.py (export/audit) · event_store.py
├── pa-knowledge/           # productagents.knowledge.*  — storage spine + knowledge services
│   └── src/productagents/knowledge/  # sink.py · container.py · repositories/sqlmodel · services/{feedback,initiative,metrics}
├── pa-connectors/          # productagents.connectors.*  — Layer-1 connector framework
│   └── src/productagents/connectors/
│       ├── base.py · http.py · registry.py · runtime.py  # the framework
│       ├── connector_errors.py · observability.py        # error classifier + span logger
│       └── github/         #   first connector: issues → CustomerFeedback
└── pa-platform/            # productagents.platform.*  — Application Services + Event Bus + Session + composition root
    └── src/productagents/platform/
        ├── bus.py          #   EventBus (publish/subscribe/close)
        ├── events.py       #   platform event vocabulary (SessionStarted → SessionFinished/SessionFailed)
        ├── session.py      #   Session value type
        ├── decision_service.py  #   DecisionService (start_session, runner→event translation, recording)
        ├── connector_service.py #   ConnectorService (sync + health-check composition root)
        ├── context.py      #   open_decision_context (per-run AgentContext + DB session); also exposes open_event_store
        ├── serialization.py     #   platform Event <-> Event-Store row bridge (pydantic TypeAdapter)
        ├── session_service.py   #   SessionService — list/get/replay persisted sessions
        ├── workflow.py          #   WorkflowService — registry over the decision pipeline (evaluate_initiative)
        ├── workspace.py         #   WorkspaceService — a workspace is a directory of local state (DB/connectors/.env/logs)
        ├── connectors.py   #   connector YAML loading + sync runtime (relocated from pa-app)
        ├── llm.py          #   re-exports get_model + DEFAULT_MODEL (platform seam)
        ├── evidence.py     #   re-exports collect_evidence / load_scenario / EvidenceError
        ├── reflection.py   #   re-exports reflect (platform seam)
        └── prompt_service.py  #   PromptService — Application-Layer face of the prompt registry
tests/                      # offline suite, FakeChatModel (see tests/CLAUDE.md)
docs/design/adr/            # Architecture Decision Records
desktop/                    # V3 Tauri + React desktop GUI (presentation adapter). Spawns
                            #   `productagents ipc` as a sidecar; talks NDJSON over stdio to the Application
                            #   Layer. Not a uv workspace member (it is a JS/Rust app). See `README.md`.
```

**Import path examples:**
```python
from productagents.core.models import DecisionRecord, Recommendation, Initiative
from productagents.core.models import CustomerFeedback, Feature, ProductMetric
from productagents.core.config import settings
from productagents.agents.graph import build_graph
from productagents.agents.runner import run_decision
from productagents.agents.evidence import collect_evidence
from productagents.platform import DecisionService, ConnectorService, SessionService
from productagents.platform import WorkflowService
from productagents.platform import Workspace, WorkspaceService
from productagents.platform import PromptService
from productagents.platform.events import SessionFinished, SessionFailed
from productagents.platform.llm import DEFAULT_MODEL, get_model
from productagents.platform.serialization import serialize_event, deserialize_event
from productagents.app.setup import check_config
from productagents.app.cli import main  # console entry point (no subcommand → prints help)
import productagents.memory as memory
from productagents.memory.event_store import EventStore
```

Each key sub-directory has its own `CLAUDE.md` with the local contract.

## Commands

This project uses **uv** (not Conda, despite the README's "Technology Stack" note). Requires Python ≥ 3.14.

A root **`Makefile`** wraps the common workflows behind one entrypoint — run `make help` to list targets (`make setup` for first-time install, `make check` for the full lint+type+test gate, `make gui` to launch, `make clean`/`make clean-all` to tidy). The raw commands it wraps are below.

```bash
uv sync                 # install deps + all workspace members (incl. dev group)
uv run productagents    # print CLI help
uv run productagents sync   # headless one-shot connector sync (for cron/launchd); exits non-zero on failure
uv run productagents run evaluate_initiative "My initiative" --evidence sample  # headless decision run, streams events
uv run productagents workspace list          # list workspaces (active marked with *)
uv run productagents workspace show [name]   # show a workspace's on-disk paths (defaults to active)
uv run productagents sessions list           # list persisted runtime sessions
uv run productagents sessions show <id>      # replay a session's event timeline
uv run productagents reflect [<decision-id> "<note>"]   # list past decisions / record an outcome
uv run productagents --workspace <name> ...  # run any of the above against a named workspace
uv run pytest           # full suite — runs offline with a fake model, no API key
uv run pytest tests/test_debate.py                         # one file
uv run pytest tests/test_debate.py::test_name -x           # one test
uv run lint-imports     # verify 7 import-linter layer contracts (layers + forbidden)
uv run ruff check packages tests  # lint all source and test trees
uv run ty check         # type check (pyright-based)
cd desktop && npm run tauri dev   # launch the V3 desktop GUI (dev; spawns the ipc sidecar)
```

`uv sync` resolves all seven workspace members (`packages/*`) together. `pytest` auto-runs coverage (`--cov`, configured in `pyproject.toml`) and writes `htmlcov/`. `[tool.coverage.paths]` maps each member's `src/productagents/` tree back to the namespace so coverage spans all packages. `asyncio_mode = "auto"`, so `async def test_*` functions need no decorator.

### Runtime configuration (env vars)

- `PRODUCTAGENTS_MODEL` — provider-prefixed model id, default `anthropic:claude-sonnet-4-6`. For non-LangChain-native providers also set `PRODUCTAGENTS_MODEL_PROVIDER`. Provide the matching key (e.g. `ANTHROPIC_API_KEY`).
- `PRODUCTAGENTS_DEBATE_ROUNDS` — debate rounds, default 2 (each round = one advocate argument + one skeptic rebuttal).
- `PRODUCTAGENTS_JUDGE_THRESHOLD` — judge pass threshold for both rubric dimensions (evidence grounding, rationale coherence), default 0.7.
- `PRODUCTAGENTS_JUDGE_MAX_RETRIES` — max strategist revisions the judge can trigger, default 1. `0` makes the judge score-only (it never loops back to the strategist).
- `PRODUCTAGENTS_MAX_RETRIES` — automatic retry budget (with backoff) for transient provider errors (e.g. free-tier OpenRouter 429/5xx), default 6.
- `PRODUCTAGENTS_LOG_FILE` — path of the rotating log file (default `productagents.log`). Logging is **file-only** (the CLI streams events to stdout; the GUI consumes IPC).
- `PRODUCTAGENTS_LOG_LEVEL` — `DEBUG`/`INFO`/`WARNING`/`ERROR` (default `INFO`; invalid values fall back to `INFO`). `DEBUG` logs every structured LLM call; failures (including a model that returns no structured output) are logged at `ERROR` with a full traceback.
- `PRODUCTAGENTS_HOME` — directory holding all workspaces (default `~/.productagents`; workspaces live under `<home>/workspaces/<name>/`).
- `PRODUCTAGENTS_WORKSPACE` — name of the active workspace (default `default`). On launch the platform resolves this workspace, creates its directory if absent, and **activates** it: the workspace's `productagents.db`, `connectors.yaml`, `.env`, and `productagents.log` become the defaults by setting `PRODUCTAGENTS_DB_URL` / `PRODUCTAGENTS_CONNECTORS_FILE` / `PRODUCTAGENTS_LOG_FILE` (an explicit export of any of these still wins) and loading the workspace `.env`.
- `PRODUCTAGENTS_PROMPTS_DIR` — directory of per-workspace prompt overrides (default `<workspace.root>/prompts`, set by `WorkspaceService.activate`). Each prompt is `<dir>/<name>/NNNN.txt`; the highest number is active; version 0 is the bundled default. An explicit export wins (`setdefault`).

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

Readiness and setup live in the desktop **Settings** panel (`config.get` / `config.set` IPC methods); for the CLI, edit the active workspace `.env` directly. The check is static — it never makes a network call.

## Architecture

The orchestration is a **LangGraph `StateGraph`** assembled in `graph.py`. `GraphState` is a `TypedDict`; the five analysts run in parallel from `START`, so `reports` is an `Annotated[list, operator.add]` reducer that merges their concurrent writes. All five fan in to `debate`, then `strategist`, `risk`, `governance`, then `END`. The compiled graph takes a chat model by dependency injection — every node is wired with `partial(node, model=model)`. **Nodes never construct their own model**; the model comes from `llm.get_model()` (the single provider-agnostic factory) and is passed down. This is what makes tests able to inject `FakeChatModel`. The model-free `recall` node runs in parallel from `START`, selects lessons from relevant past decisions (read at the UI boundary and seeded into state, like `portfolio`), and fans into `strategist` alongside `debate`, closing the Outcome-Learning loop.

**Data flow / layers:**
- `productagents.core.models` — all Pydantic models, split by bounded context
(`discovery`/`planning`/`strategy`/`measurement` synced canonical models +
`decision` decision-run records); import from the `core.models` package surface. There are two flavours of model: the structured-output schemas an LLM call must return (`AnalystFindings`, `DebateArgument`, `Recommendation`) and the assembled/enriched records nodes build from them (`AnalystReport`, `DebateTurn`, `DecisionRecord`). Nodes call `model.with_structured_output(Schema)`.
- `productagents.agents.evidence` — pluggable Layer-1 evidence collection behind an `EvidenceSource` protocol (`collect() -> Evidence`). `ScenarioSource` reads a named scenario from `agents/data/scenarios/<name>/`; `DirectorySource` reads the same five files from any folder. `collect_evidence(spec)` resolves a user-typed string (known scenario name → `ScenarioSource`; existing directory path → `DirectorySource`; blank → bundled `sample`). Every loaded field records an `EvidenceSourceRef` on `Evidence.sources` (provenance), written onto the `DecisionRecord` and visible in the desktop app. `load_scenario(name)` remains as a thin wrapper over `ScenarioSource`.
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
- `productagents.agents.runner` — the **boundary between the graph and the UI**. `run_decision()` consumes `graph.astream(stream_mode=["updates", "custom"])` and normalizes raw chunks into plain dataclass events (`ProgressEvent`, `NodeCompleteEvent`, `DebateTurnEvent`, `FinishedEvent`, `FinalVerdictEvent`). On a governance `__interrupt__`, `run_decision` awaits the `approver` callback for a `HumanDecision` and resumes via `Command(resume=...)`. The presentation layer only ever sees these events — it has no LangGraph knowledge. The whole run is wrapped in a `decision.run` span and each node in a `decision.<node>` span (`core.observability.span`), the decision-side mirror of the connectors' `connector.sync`/`connector.health` spans.
- `productagents.platform.connectors` — connector composition root: loads `connectors.yaml` (typed, fail-fast via `plan_connectors`), builds enabled connectors against a `DbCanonicalSink`, runs `run_sync`, and persists cursors via `SyncStateStore`. The desktop app's **Connectors** panel triggers sync via `ConnectorService.sync()` and health-checks via `ConnectorService.health()`; the CLI can also run `productagents sync`. Exposed to the app as `ConnectorService`; `pa-platform` is the only package that imports `pa-connectors`.
- `productagents.app.cli` — the `productagents` console entry point (`main`). Parses subcommands (`run`, `sync`, `workspace list/show`, `sessions list/show`, `reflect`) with stdlib `argparse`; a bare `productagents` (no subcommand) prints help. The console script targets `productagents.app.cli:main`.
- `productagents.app.ipc` — JSON-over-stdio adapter (`productagents ipc`). The Tauri desktop shell spawns this as a sidecar; it serves the same Application Layer as the CLI via NDJSON. `reflection.record {decision_id, note}` is the GUI's outcome-capture write surface (guarded by a `reflection=None` kwarg).
- `productagents.memory` — DB-backed organizational-memory subsystem. `DecisionStore` persists `DecisionRecord` and `OutcomeRecord` rows in SQLite/Postgres via an injected async session; `LessonRetriever` combines lexical scoring (`LexicalRetriever`) with cosine similarity over hashing embeddings (`SemanticRetriever`) for hybrid retrieval. `LearningService` is the Knowledge-Layer face: `relevant_lessons(initiative)` → lesson strings injected into the strategist, `record_decision` / `record_outcome` on the write side. JSONL (`jsonl.py`) is export/audit only — the DB is the system of record. The `recall` node retrieves lessons through `AgentContext.learning` (a `LessonReader` slice), keeping agents free of sqlalchemy. Since V3 Phase 2 pa-memory also owns the **Event Store** (`event_store.py`): append-only `runtime_session` + `runtime_event` tables persisting every platform event of every run — the execution log that complements the decision system-of-record.
- **Outcome Learning has two halves.** The *injection* half runs inside the graph
  (`recall` → `strategist`): `recall` calls `ctx.learning.relevant_lessons(initiative)` and seeds the lessons into graph state. The *capture* half runs **outside** the graph:
  `agents/reflection.py::reflect()` is triggered by the `productagents reflect` CLI command or the desktop **Reflection** panel (via the `reflection.record` IPC method); it compares a past `DecisionRecord`'s predicted outcomes against a free-text note, and calls `ctx.learning.record_outcome` (which delegates to `LearningService` → `DecisionStore`). `recall` later reads those outcomes back via hybrid retrieval. The reflection agent is the one agent not wired into `graph.py`.

### Conventions that matter

- **Nodes degrade, never crash.** Every node wraps its LLM call in `try/except` and returns a fallback (a `failed=True` report, a placeholder debate turn, or a zero-confidence recommendation) so one failure can't abort the graph.
- **Streaming from nodes** goes through `agents/_stream.get_writer()`, not `langgraph.config.get_stream_writer()` directly. The latter raises `RuntimeError` when called outside an active graph run (e.g. a unit test invoking a node directly), so the helper returns a no-op writer in that case. Use `get_writer()` in any new node. The progress dict itself is built via `agents/stream_events.py` helpers (`emit_status`, `emit_error`, `emit_payload`, `emit_fatal`), the single source of truth for the wire keys the runner parses.
- **Testing is fully offline.** `tests/fakes.py::FakeChatModel` maps a schema class → the instance (or `Exception`) its `with_structured_output(schema).ainvoke()` should return. Test nodes by calling them directly with a `FakeChatModel`; test the graph by building it with one.
- **Nodes receive an `AgentContext`, not just a model.** `build_graph(context)` injects `ctx` into the analysts (so any analyst may reach a Knowledge Service) and `ctx.model` into the LLM-only nodes. The Customer Research analyst reads synced `CustomerFeedback` from the local store via `ctx.feedback`, degrading to the scenario evidence text when the store is empty/unavailable. The per-run DB session is opened at the platform boundary (`platform/context.py`), keeping nodes engine-free — the same pattern `recall` uses for the decision log.

## Adding a stage

To extend toward the README's full architecture (e.g. the planned Risk Evaluation layer): add the schema(s) to `productagents.core.models`, add a node in `productagents.agents.*` using `get_writer()` and structured output, wire it into `productagents.agents.graph` (and `GraphState`), surface it through `productagents.agents.runner` as a new event, and render it in the CLI and desktop GUI. Plans for upcoming work live in `docs/superpowers/plans/`.

**Layer rules** (enforced by `uv run lint-imports`):
- `pa-app` (presentation) imports only `pa-platform` and `pa-core` — never agents, memory, connectors, or their heavy deps (langgraph, langchain, sqlalchemy) directly.
- `pa-platform` is the connector composition root and the only package that imports `pa-connectors`; it exposes `DecisionService`, `ConnectorService`, and the platform event vocabulary to the presentation layer.
- `pa-agents` may import from `pa-memory`, `pa-core` — not from `pa-app` or `pa-platform`.
- `pa-memory` and `pa-knowledge` may import from `pa-core` — not from each other or above.
- `pa-core` is dependency-light: no httpx, langchain, langgraph, sqlalchemy, textual.
- `requests` is banned platform-wide (async-first, use httpx).
