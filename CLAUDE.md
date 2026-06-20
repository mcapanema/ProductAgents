# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ProductAgents is a multi-agent framework for product decision-making under uncertainty. The README describes a target seven-stage / six-layer architecture, but the repository currently implements a **thin end-to-end slice** of it. Keep that distinction in mind: the README is the vision; the code is the slice. The implemented slice is:

```
evidence → [customer_research ∥ product_analytics] → debate (advocate vs skeptic) → strategist → decisions.jsonl
```

Everything runs live in a Textual TUI.

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

The orchestration is a **LangGraph `StateGraph`** assembled in `graph.py`. `GraphState` is a `TypedDict`; the two analysts run in parallel from `START`, so `reports` is an `Annotated[list, operator.add]` reducer that merges their concurrent writes. Both fan in to `debate`, then `strategist`, then `END`. The compiled graph takes a chat model by dependency injection — every node is wired with `partial(node, model=model)`. **Nodes never construct their own model**; the model comes from `llm.get_model()` (the single provider-agnostic factory) and is passed down. This is what makes tests able to inject `FakeChatModel`.

**Data flow / layers:**
- `schemas.py` — all Pydantic models, shared across nodes, graph state, and the JSONL persistence. There are two flavours of model: the structured-output schemas an LLM call must return (`AnalystFindings`, `DebateArgument`, `Recommendation`) and the assembled/enriched records nodes build from them (`AnalystReport`, `DebateTurn`, `DecisionRecord`). Nodes call `model.with_structured_output(Schema)`.
- `evidence.py` — loads a named scenario (markdown + JSON) from `data/scenarios/<name>/`. The TUI loads the bundled `sample` scenario.
- `agents/` — one node per file. Analysts and the strategist each issue a single structured LLM call; `debate.py` loops rounds, alternating advocate/skeptic personas, each turn seeing the full transcript so far.
- `runner.py` — the **boundary between the graph and the UI**. `run_decision()` consumes `graph.astream(stream_mode=["updates", "custom"])` and normalizes raw chunks into plain dataclass events (`ProgressEvent`, `NodeCompleteEvent`, `DebateTurnEvent`, `FinishedEvent`). The TUI only ever sees these events — it has no LangGraph knowledge.
- `tui/app.py` — Textual app. `main()` is the `productagents` entry point. It runs the graph in a `@work` worker, updates panels per event, and on `FinishedEvent` appends a `DecisionRecord` via an injected `recorder` (default `memory.record_decision`).
- `memory.py` — append-only `decisions.jsonl` log (the "organizational memory" stub).

### Conventions that matter

- **Nodes degrade, never crash.** Every node wraps its LLM call in `try/except` and returns a fallback (a `failed=True` report, a placeholder debate turn, or a zero-confidence recommendation) so one failure can't abort the graph.
- **Streaming from nodes** goes through `agents/_stream.get_writer()`, not `langgraph.config.get_stream_writer()` directly. The latter raises `RuntimeError` when called outside an active graph run (e.g. a unit test invoking a node directly), so the helper returns a no-op writer in that case. Use `get_writer()` in any new node.
- **Testing is fully offline.** `tests/fakes.py::FakeChatModel` maps a schema class → the instance (or `Exception`) its `with_structured_output(schema).ainvoke()` should return. Test nodes by calling them directly with a `FakeChatModel`; test the graph by building it with one.

## Adding a stage

To extend toward the README's full architecture (e.g. the planned Risk Evaluation layer): add the schema(s) to `schemas.py`, add a node in `agents/` using `get_writer()` and structured output, wire it into `graph.py` (and `GraphState`), surface it through `runner.py` as a new event, and render it in `tui/app.py`. Plans for upcoming work live in `docs/superpowers/plans/`.
