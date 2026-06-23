# src/productagents/ — package map

The implemented slice of the framework. Read top-level `CLAUDE.md` first for the
vision-vs-slice framing and the end-to-end diagram. This file maps the package's
own layers.

## Layers (data flows top to bottom)

| Module | Responsibility |
| --- | --- |
| `schemas.py` | All Pydantic models + the shared `Literal` vocabularies (`Verdict`, `RiskLevel`, `DebateSide`, `DecidedBy`). Two families: **LLM-output** schemas a structured call must return (`AnalystFindings`, `DebateArgument`, `RiskFinding`, `GovernanceFinding`, `Reflection`, `Recommendation`) and **assembled records** nodes build from them (`AnalystReport`, `DebateTurn`, `RiskAssessment`, `GovernanceVerdict`, `OutcomeRecord`, `DecisionRecord`). |
| `evidence.py` | Layer-1 evidence collection behind the `EvidenceSource` protocol. `ScenarioSource` (named bundled scenario) and `DirectorySource` (any folder) both go through `_collect_from_dir`, which records an `EvidenceSourceRef` per loaded field. `collect_evidence(spec)` resolves a user string → source. |
| `llm.py` | The single provider-agnostic `get_model()` factory. **Nodes never call this** — the model is injected into the graph and passed to each node via `partial`. An `openrouter:` model prefix routes through `langchain-openrouter` (`ChatOpenRouter`); the prefix is split on the first colon so a `:free` suffix survives. OpenRouter free models must support tool/function calling, since every node uses `with_structured_output`. `PRODUCTAGENTS_MAX_RETRIES` (default 6) sets the client's retry-with-backoff budget for transient provider errors. |
| `llm_errors.py` | Provider-agnostic classification of LLM call failures. `classify_provider_error(exc)` maps any exception (by HTTP status, class name, and message text — no SDK import) to a `ProviderError` with a `category` (`rate_limit`/`auth`/`tool_calling_unsupported`/`upstream`/`unknown`), a friendly message, and a `fatal` flag. Fatal categories let the run stop early instead of degrading every node. `StructuredOutputError` (the `None`-result/tool-calling case) is a fatal `ProviderError` subclass. |
| `setup.py` | Static config-readiness check + `.env` provisioning. `check_config()` resolves provider→key-var and verifies the key is set (no network). `write_env()` persists collected values via `python-dotenv` and `os.environ`. Used by the TUI's home/setup screens, **not** by graph nodes. |
| `logging_config.py` | `configure_logging()` — installs a single rotating **file** handler on the `productagents` logger (`propagate=False`, no stdout/stderr) so the TUI is never corrupted. Env: `PRODUCTAGENTS_LOG_FILE`, `PRODUCTAGENTS_LOG_LEVEL`. Called once in `main()` after `load_env()`. |
| `agents/` | One graph node per file. See `agents/CLAUDE.md`. |
| `graph.py` | Wires nodes into a LangGraph `StateGraph`. Owns `GraphState` (`TypedDict`). `build_graph(model, *, human_in_the_loop=False)` injects the model into every node and optionally appends `human_approval` with an `InMemorySaver` checkpointer. |
| `runner.py` | The boundary between the graph and any UI. `run_decision()` consumes `graph.astream(stream_mode=["updates","custom"])` and yields plain dataclass events (`ProgressEvent`, `NodeCompleteEvent`, `DebateTurnEvent`, `RiskAssessmentEvent`, `GovernanceVerdictEvent`, `FinalVerdictEvent`, `RecallEvent`, `JudgmentEvent`, `RecommendationEvent` (emitted each time the strategist produces a recommendation, including judge-retry revisions — lets the TUI render the strategist panel live before `FinishedEvent`), `FinishedEvent`). Handles the governance `__interrupt__` by awaiting the `approver` and resuming with `Command(resume=...)`. |
| `memory.py` | Append-only `decisions.jsonl` / `outcomes.jsonl` logs + `select_relevant_lessons()` (the read side of Outcome Learning). Returns outcome-backed lessons first, then prediction-style "derived" lessons synthesized from similar past decisions that have no captured outcome yet (marked "not yet validated"; repeated same-initiative runs deduped), so the panel is useful before any reflection. |
| `tui/` | The Textual app and its modal screens. See `tui/CLAUDE.md`. |
| `data/scenarios/<name>/` | Bundled mock evidence: `customer_feedback.md`, `product_analytics.json`, `market_intelligence.md`, `business_metrics.json`, `technical_context.md`. Only the first two are required; the rest default to empty. |

## Two graph entry points, one model

`graph.py` is the only module that knows LangGraph's shape; `runner.py` is the
only module that knows how to drive it. Everything above `runner` sees just the
event dataclasses. The chat model is created once (`get_model()` in `tui/app.py`)
and threaded down by dependency injection — this is what lets every test inject
`tests/fakes.py::FakeChatModel` instead of a real provider.

## Conventions

- **Nodes degrade, never crash** — every LLM call is wrapped in `try/except
  Exception` (`# noqa: BLE001`) returning a fallback record.
- **Concurrent writes use reducers** — five analysts run in parallel from `START`,
  so `GraphState.reports` is `Annotated[list, operator.add]`.
- **State is seeded at the UI boundary** — `portfolio`/`outcomes` are read from
  the logs in `tui/app.py` and passed into `run_decision`; nodes never touch the
  filesystem (keeps `recall`/`governance` pure and testable).

## Adding a stage

Add the schema(s) → add a node in `agents/` (`get_writer()` + structured output)
→ wire into `graph.py` and `GraphState` → surface a new event in `runner.py` →
render it in `tui/app.py`. Plans live in `docs/superpowers/plans/`.
