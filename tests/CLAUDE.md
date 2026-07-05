# tests/ — testing conventions

Everything runs **offline**. No test may require an API key or hit a network.

## Run

```bash
uv run pytest                                   # full suite + coverage
uv run pytest tests/test_debate.py              # one file
uv run pytest tests/test_debate.py::test_x -x   # one test, stop on first failure
```

Coverage runs automatically (`--cov`, `--cov-fail-under=90`, writes `htmlcov/`).
`asyncio_mode = "auto"` — write `async def test_*` with no decorator.

## The fake model

`tests/fakes.py::FakeChatModel` is the substitute for a LangChain chat model. It
maps a Pydantic **schema class** → the instance its
`with_structured_output(schema).ainvoke(...)` should return. Map the value to an
`Exception` instance to exercise a node's graceful-degradation path.

```python
model = FakeChatModel({AnalystFindings: AnalystFindings(findings=[...], signals=[...])})
model = FakeChatModel({AnalystFindings: RuntimeError("LLM down")})  # degrade path
```

## What to test where

- **A node:** call `await some_node(state, model)` directly with a hand-built
  `state` dict and a `FakeChatModel`. Assert on the returned partial state. The
  `get_writer()` no-op makes this work outside a graph run.
- **The graph:** `build_graph(FakeChatModel({...}))`, then drive it through
  `run_decision` (`tests/test_runner.py`, `tests/test_graph.py`).
- **The presentation edges:** call the handlers directly with fake services
  injected by keyword — CLI (`tests/test_cli.py`), NDJSON IPC
  (`tests/test_ipc.py`), dev WebSocket bridge (`tests/test_devbridge.py`).
  No real model, stdin, or socket.
- **Connectors:** mock httpx with `respx`; write to
  `tests/connector_fakes.py::FakeSink`, never a real store.
- **The desktop GUI** has its own runners (Vitest unit + Playwright e2e) —
  see `desktop/CLAUDE.md` and `desktop/e2e/CLAUDE.md`.
- **Pure helpers** (`_format`, `memory.select_relevant_lessons`, `evidence`):
  call directly, no model needed.

## Conventions

- Each test builds its own `state`/fixtures; no shared mutable global state.
- For every node, cover the happy path **and** the degrade path (the failure
  fallback is part of the contract — keep it covered to hold the 90% gate).
- Env-var-driven behavior is tested with `monkeypatch.setenv/​delenv`
  (e.g. `test_debate.py` for `PRODUCTAGENTS_DEBATE_ROUNDS`).
