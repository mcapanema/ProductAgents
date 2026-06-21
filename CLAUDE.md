# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ProductAgents is a multi-agent framework for product decision-making under uncertainty. The README describes a target seven-stage / six-layer architecture, but the repository currently implements a **thin end-to-end slice** of it. Keep that distinction in mind: the README is the vision; the code is the slice. The implemented slice is:

```
evidence → [customer_research ∥ product_analytics ∥ market ∥ business ∥ technical] → debate (advocate vs skeptic) ┐
                                                                  recall (past lessons) ┴→ strategist → risk → governance (advisory) → human_approval → decisions.jsonl
```

Everything runs live in a Textual TUI.

## Directory structure

```
src/productagents/
├── schemas.py            # all Pydantic models + shared Literal vocabularies
├── evidence.py           # Layer-1 EvidenceSource protocol + scenario/dir sources
├── llm.py                # get_model() — the only provider-agnostic factory
├── graph.py              # LangGraph StateGraph assembly + GraphState
├── runner.py             # graph→UI boundary: normalizes the stream into events
├── memory.py             # decisions.jsonl / outcomes.jsonl + lesson retrieval
├── agents/               # one graph node per file (see agents/CLAUDE.md)
│   ├── _analyst.py       #   shared run_analyst() executor for the 5 analysts
│   ├── _format.py        #   shared prompt formatters
│   ├── _stream.py        #   get_writer() progress-event helper
│   ├── customer_research.py · product_analytics.py · market.py
│   ├── business.py · technical.py            # the five parallel analysts
│   ├── recall.py · strategist.py · risk.py · governance.py
│   ├── human_approval.py # HITL interrupt node (added only when enabled)
│   └── reflection.py     # OUT OF GRAPH: post-hoc outcome reflection
├── tui/                  # Textual app + modal screens (see tui/CLAUDE.md)
│   ├── app.py · app.tcss · approval.py · reflection.py
└── data/scenarios/<name>/  # bundled mock evidence files
tests/                    # offline suite, FakeChatModel (see tests/CLAUDE.md)
```

Each key directory has its own `CLAUDE.md` with the local contract.

## Commands

This project uses **uv** (not Conda, despite the README's "Technology Stack" note). Requires Python ≥ 3.14.

```bash
uv sync                 # install deps (incl. dev group)
uv run productagents    # launch the TUI
uv run pytest           # full suite — runs offline with a fake model, no API key
uv run pytest tests/test_debate.py                         # one file
uv run pytest tests/test_debate.py::test_name -x           # one test
```

`pytest` auto-runs coverage (`--cov`, configured in `pyproject.toml`) and writes `htmlcov/`. `asyncio_mode = "auto"`, so `async def test_*` functions need no decorator.

### Runtime configuration (env vars)

- `PRODUCTAGENTS_MODEL` — provider-prefixed model id, default `anthropic:claude-sonnet-4-6`. For non-LangChain-native providers also set `PRODUCTAGENTS_MODEL_PROVIDER`. Provide the matching key (e.g. `ANTHROPIC_API_KEY`).
- `PRODUCTAGENTS_DEBATE_ROUNDS` — debate rounds, default 2 (each round = one advocate argument + one skeptic rebuttal).

## Architecture

The orchestration is a **LangGraph `StateGraph`** assembled in `graph.py`. `GraphState` is a `TypedDict`; the five analysts run in parallel from `START`, so `reports` is an `Annotated[list, operator.add]` reducer that merges their concurrent writes. All five fan in to `debate`, then `strategist`, `risk`, `governance`, then `END`. The compiled graph takes a chat model by dependency injection — every node is wired with `partial(node, model=model)`. **Nodes never construct their own model**; the model comes from `llm.get_model()` (the single provider-agnostic factory) and is passed down. This is what makes tests able to inject `FakeChatModel`. The model-free `recall` node runs in parallel from `START`, selects lessons from relevant past decisions (read at the UI boundary and seeded into state, like `portfolio`), and fans into `strategist` alongside `debate`, closing the Outcome-Learning loop.

**Data flow / layers:**
- `schemas.py` — all Pydantic models, shared across nodes, graph state, and the JSONL persistence. There are two flavours of model: the structured-output schemas an LLM call must return (`AnalystFindings`, `DebateArgument`, `Recommendation`) and the assembled/enriched records nodes build from them (`AnalystReport`, `DebateTurn`, `DecisionRecord`). Nodes call `model.with_structured_output(Schema)`.
- `evidence.py` — pluggable Layer-1 evidence collection behind an `EvidenceSource` protocol (`collect() -> Evidence`). `ScenarioSource` reads a named scenario from `data/scenarios/<name>/`; `DirectorySource` reads the same five files from any folder. `collect_evidence(spec)` resolves a user-typed string (known scenario name → `ScenarioSource`; existing directory path → `DirectorySource`; blank → bundled `sample`). Every loaded field records an `EvidenceSourceRef` on `Evidence.sources` (provenance), which the TUI persists on the `DecisionRecord`. `load_scenario(name)` remains as a thin wrapper over `ScenarioSource`.
- `agents/` — one node per file. The five analysts share a single executor (`agents/_analyst.py::run_analyst`) and
  differ only in their `_prompt`; the strategist issues its own single structured
  call. `debate.py` loops rounds, alternating advocate/skeptic personas, each turn
  seeing the full transcript so far. Shared prompt formatters live in
  `agents/_format.py`.
- `graph.py` — wires nodes into the StateGraph. When `human_in_the_loop=True`, `build_graph(model, human_in_the_loop=True)` appends a `human_approval` node after `governance` and compiles the graph with an `InMemorySaver` checkpointer so it can `interrupt()` and resume.
- `runner.py` — the **boundary between the graph and the UI**. `run_decision()` consumes `graph.astream(stream_mode=["updates", "custom"])` and normalizes raw chunks into plain dataclass events (`ProgressEvent`, `NodeCompleteEvent`, `DebateTurnEvent`, `FinishedEvent`, `FinalVerdictEvent`). On a governance `__interrupt__`, `run_decision` awaits the `approver` callback for a `HumanDecision` and resumes via `Command(resume=...)`. The TUI only ever sees these events — it has no LangGraph knowledge.
- `tui/app.py` — Textual app. `main()` is the `productagents` entry point. It runs the graph in a `@work` worker, updates panels per event. On a governance `__interrupt__`, `run_decision` calls `_ask_human`, which pushes the `ApprovalScreen` modal (`tui/approval.py`) via `push_screen_wait` so the human can approve, reject, or request further analysis; the human's choice resumes the graph. `FinalVerdictEvent` then arrives and updates the governance panel. On `FinishedEvent`, appends a `DecisionRecord` via an injected `recorder` (default `memory.record_decision`). The TUI has a second input for the evidence source (scenario name or folder path; blank = bundled `sample`); it resolves evidence per run via `collect_evidence`, renders the resolved provenance in an "Evidence Sources" panel, and writes `evidence_sources` onto the `DecisionRecord`.
- `memory.py` — append-only `decisions.jsonl` and `outcomes.jsonl` logs (the "organizational memory"). `select_relevant_lessons()` scores past decisions by lexical similarity to the current initiative and returns the lessons of the closest matches — this is the read side of Outcome Learning.
- **Outcome Learning has two halves.** The *injection* half runs inside the graph
  (`recall` → `strategist`). The *capture* half runs **outside** the graph:
  `agents/reflection.py::reflect()` is triggered from the TUI's reflection screen
  (`ctrl+r`, `tui/reflection.py`), compares a past `DecisionRecord`'s predicted
  outcomes against a free-text note, and appends an `OutcomeRecord` to
  `outcomes.jsonl` via `memory.record_outcome`. `recall` later reads those
  outcomes back. The reflection agent is the one agent not wired into `graph.py`.

### Conventions that matter

- **Nodes degrade, never crash.** Every node wraps its LLM call in `try/except` and returns a fallback (a `failed=True` report, a placeholder debate turn, or a zero-confidence recommendation) so one failure can't abort the graph.
- **Streaming from nodes** goes through `agents/_stream.get_writer()`, not `langgraph.config.get_stream_writer()` directly. The latter raises `RuntimeError` when called outside an active graph run (e.g. a unit test invoking a node directly), so the helper returns a no-op writer in that case. Use `get_writer()` in any new node.
- **Testing is fully offline.** `tests/fakes.py::FakeChatModel` maps a schema class → the instance (or `Exception`) its `with_structured_output(schema).ainvoke()` should return. Test nodes by calling them directly with a `FakeChatModel`; test the graph by building it with one.

## Adding a stage

To extend toward the README's full architecture (e.g. the planned Risk Evaluation layer): add the schema(s) to `schemas.py`, add a node in `agents/` using `get_writer()` and structured output, wire it into `graph.py` (and `GraphState`), surface it through `runner.py` as a new event, and render it in `tui/app.py`. Plans for upcoming work live in `docs/superpowers/plans/`.
