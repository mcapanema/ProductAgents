# OpenRouter Free-Model Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ProductAgents run its full pipeline on OpenRouter's free models by declaring the `langchain-openrouter` dependency, defaulting the OpenRouter provider to a free tool-calling-capable model, and documenting the one caveat that matters.

**Architecture:** OpenRouter support is almost entirely pre-wired. `langchain`'s `init_chat_model` already maps an `openrouter:` model prefix to `langchain_openrouter.ChatOpenRouter`; `setup.py` already lists the `openrouter` provider with `OPENROUTER_API_KEY`; the setup screen already exposes it; and `init_chat_model`'s `_parse_model` splits the provider prefix on the *first* colon only, so a free-model id like `openrouter:deepseek/deepseek-chat-v3-0324:free` keeps its `:free` suffix intact. The **only** functional gap is that `langchain-openrouter` is not a declared/installed dependency, so `get_model()` raises on import. This plan adds that dependency, swaps the OpenRouter default model from the paid `openrouter:openai/gpt-4o` to a free model, and documents that free models must support tool/function calling (because every node calls `model.with_structured_output(Schema)`, which defaults to `method="function_calling"`; a model without tool support makes every node silently degrade to its fallback record).

**Tech Stack:** Python ≥3.14, uv, LangChain 1.x (`langchain`, `langchain-openrouter`), LangGraph, pytest (offline, no network/API key).

## Global Constraints

- Requires Python ≥ 3.14; project is managed with **uv** (not pip/conda). Install deps with `uv sync`; run anything with `uv run …`.
- Tests are **fully offline** — no test may require a real API key or hit the network. Dummy env values via `monkeypatch.setenv` are fine; constructing `ChatOpenRouter` does not make a network call.
- Coverage gate is enforced: `--cov-fail-under=90` (configured in `pyproject.toml`). Every new code path needs a test.
- Provider default-model ids must keep the `provider:` prefix — `tests/test_setup.py::test_providers_all_have_default_model_with_provider_prefix` asserts `info.default_model.startswith(f"{pid}:")` for every provider.
- Nodes never construct their own model and never call `get_model()`; the model is dependency-injected. This plan touches only `llm.py` resolution, `setup.py` provider metadata, deps, tests, and docs — no node/graph/runner/TUI logic changes.
- Free OpenRouter models must support **tool/function calling** to drive this pipeline, because `with_structured_output` defaults to `method="function_calling"`. The chosen default (`deepseek/deepseek-chat-v3-0324:free`) supports it.

---

## File Structure

| File | Change | Responsibility |
| --- | --- | --- |
| `pyproject.toml` | Modify (`dependencies`) | Declare `langchain-openrouter` so `init_chat_model`'s `openrouter` provider can be imported. |
| `tests/test_llm.py` | Modify (add test) | Prove `get_model()` resolves an `openrouter:…:free` id to a real `ChatOpenRouter` with the `:free` suffix preserved (guards both the new dependency and the colon-parsing). |
| `src/productagents/setup.py` | Modify (`PROVIDERS["openrouter"]`) | Default the OpenRouter provider to a free, tool-calling-capable model instead of paid `openai/gpt-4o`. |
| `tests/test_setup.py` | Modify (add test) | Lock the OpenRouter default to the chosen free model id. |
| `README.md` | Modify (`### Configure a model`) | Document the OpenRouter free-model path + the tool-calling caveat + rate-limit note. |
| `src/productagents/CLAUDE.md` | Modify (`llm.py` row) | Note that the `openrouter:` prefix routes to `langchain-openrouter` and that free models must support tool calling. |

---

### Task 1: Declare the `langchain-openrouter` dependency

This is the one functional fix. Without the package, `get_model()` with an `openrouter:` model raises `ImportError` from inside `init_chat_model`. The test is written first and fails for exactly that reason; adding the dep makes it pass.

**Files:**
- Modify: `pyproject.toml` (the `[project].dependencies` array, around lines 6-14)
- Test: `tests/test_llm.py` (append a new test)

**Interfaces:**
- Consumes: `productagents.llm.get_model()` — reads `PRODUCTAGENTS_MODEL` / `PRODUCTAGENTS_MODEL_PROVIDER` from the env and returns a LangChain chat model via `init_chat_model`.
- Produces: nothing new for later tasks; this task guarantees `get_model()` returns a `langchain_openrouter.ChatOpenRouter` instance for an `openrouter:` model id, with the provider prefix stripped and any `:free` suffix preserved on `.model`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_llm.py`:

```python
def test_openrouter_free_model_resolves_to_chatopenrouter(monkeypatch):
    """An `openrouter:…:free` id resolves to a real ChatOpenRouter.

    This exercises the real `init_chat_model` (no monkeypatching of it), so it
    proves both that `langchain-openrouter` is installed and that the provider
    prefix is split off while the `:free` suffix is preserved. Constructing the
    model makes no network call; the dummy key is never used.
    """
    monkeypatch.setenv(
        "PRODUCTAGENTS_MODEL", "openrouter:deepseek/deepseek-chat-v3-0324:free"
    )
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-a-real-key")

    model = llm.get_model()

    assert type(model).__name__ == "ChatOpenRouter"
    # init_chat_model strips the `openrouter:` provider prefix (first colon only)
    # and keeps the rest verbatim — including the `:free` suffix.
    assert model.model == "deepseek/deepseek-chat-v3-0324:free"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_llm.py::test_openrouter_free_model_resolves_to_chatopenrouter -v`
Expected: FAIL — `init_chat_model` raises `ImportError` (cannot import `langchain_openrouter`), because the package is not yet a dependency. (If it errors during import collection instead, that still counts as the red state.)

- [ ] **Step 3: Add the dependency**

In `pyproject.toml`, add `langchain-openrouter>=0.2` to the `[project].dependencies` array. After the edit the array reads:

```toml
dependencies = [
    "langgraph>=0.6",
    "langchain>=1.0",
    "langchain-anthropic>=0.3",
    "textual>=4.0",
    "pydantic>=2.7",
    "python-dotenv>=1.0",
    "langchain-google-genai>=2.0",
    "langchain-openrouter>=0.2",
]
```

- [ ] **Step 4: Sync the environment**

Run: `uv sync`
Expected: resolves and installs `langchain-openrouter` (and its transitive `openrouter` SDK) with no conflicts. `langchain-openrouter` 0.2.x requires `langchain-core<2.0.0,>=1.3.2`, which the project already satisfies.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_llm.py::test_openrouter_free_model_resolves_to_chatopenrouter -v`
Expected: PASS.

- [ ] **Step 6: Run the existing llm tests to confirm no regression**

Run: `uv run pytest tests/test_llm.py -v`
Expected: PASS — the two existing tests (`test_default_model_used_when_env_unset`, `test_env_overrides_model_and_provider`) still pass; they monkeypatch `init_chat_model` and are unaffected.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock tests/test_llm.py
git commit -m "feat: support OpenRouter via langchain-openrouter dependency

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K4CL9L3nUUqmh2bMp6Vwqn"
```

---

### Task 2: Default the OpenRouter provider to a free model

The user wants the *free* models. The setup screen pre-fills its model input from `PROVIDERS[pid].default_model`, so changing this value makes "pick OpenRouter" default to a free model in the wizard. The chosen model — `deepseek/deepseek-chat-v3-0324:free` — supports tool/function calling, which the pipeline requires (`with_structured_output` defaults to `method="function_calling"`). It is configurable: users can type any other free id (e.g. `openrouter:meta-llama/llama-3.3-70b-instruct:free`, `openrouter:google/gemini-2.0-flash-exp:free`) into the model field or `PRODUCTAGENTS_MODEL`.

**Files:**
- Modify: `src/productagents/setup.py:39-41` (the `PROVIDERS["openrouter"]` entry)
- Test: `tests/test_setup.py` (append a new test)

**Interfaces:**
- Consumes: `productagents.setup.PROVIDERS` — `dict[str, ProviderInfo]`; `ProviderInfo` has fields `label: str`, `key_var: str`, `default_model: str`.
- Produces: `PROVIDERS["openrouter"].default_model == "openrouter:deepseek/deepseek-chat-v3-0324:free"`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_setup.py`:

```python
def test_openrouter_default_is_a_free_tool_calling_model():
    """The OpenRouter provider defaults to a free model.

    The pipeline drives every node through `with_structured_output`
    (`method="function_calling"` by default), so the default free model must
    support tool/function calling — deepseek-chat-v3 does.
    """
    info = PROVIDERS["openrouter"]
    assert info.default_model == "openrouter:deepseek/deepseek-chat-v3-0324:free"
    assert info.default_model.endswith(":free")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_setup.py::test_openrouter_default_is_a_free_tool_calling_model -v`
Expected: FAIL — `default_model` is still `"openrouter:openai/gpt-4o"`, so the assertion fails.

- [ ] **Step 3: Change the default model**

In `src/productagents/setup.py`, replace the `openrouter` entry:

```python
    "openrouter": ProviderInfo(
        "OpenRouter",
        "OPENROUTER_API_KEY",
        "openrouter:deepseek/deepseek-chat-v3-0324:free",
    ),
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_setup.py::test_openrouter_default_is_a_free_tool_calling_model -v`
Expected: PASS.

- [ ] **Step 5: Run the full setup test file to confirm no regression**

Run: `uv run pytest tests/test_setup.py tests/test_setup_tui.py -v`
Expected: PASS — in particular `test_providers_all_have_default_model_with_provider_prefix` still passes (the new id starts with `openrouter:`), and `test_providers_covers_all_expected_keys` is unaffected (the key var is unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/productagents/setup.py tests/test_setup.py
git commit -m "feat: default OpenRouter provider to a free model

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K4CL9L3nUUqmh2bMp6Vwqn"
```

---

### Task 3: Document the OpenRouter free-model path and its caveat

Docs-only task. No test. The one non-obvious thing a user must know: free models without tool/function calling will make every node degrade to its fallback record (zero-confidence recommendation, `failed=True` reports) instead of crashing — so they must pick a tool-calling-capable free model and expect free-tier rate limits.

**Files:**
- Modify: `README.md` (after the `### Configure a model` section, around lines 524-530)
- Modify: `src/productagents/CLAUDE.md` (the `llm.py` row of the Layers table)

- [ ] **Step 1: Add an OpenRouter subsection to the README**

In `README.md`, immediately after the existing "To use another provider…" example block (the one ending with `export OPENAI_API_KEY="sk-..."` near line 530), insert:

```markdown
#### OpenRouter free models

[OpenRouter](https://openrouter.ai) exposes many models — including a free
tier — behind one API key. Set a `openrouter:`-prefixed model id and your
OpenRouter key:

```bash
export PRODUCTAGENTS_MODEL="openrouter:deepseek/deepseek-chat-v3-0324:free"
export OPENROUTER_API_KEY="sk-or-..."
```

Leave `PRODUCTAGENTS_MODEL_PROVIDER` unset — the `openrouter:` prefix selects
the provider, and the `:free` suffix is preserved as part of the model id.

**Pick a model that supports tool/function calling.** Every stage in the
pipeline uses structured output (`with_structured_output`, which defaults to
function calling), so a free model without tool support will make each node
fall back to a placeholder result rather than fail loudly. Known-good free
options include `deepseek/deepseek-chat-v3-0324:free`,
`meta-llama/llama-3.3-70b-instruct:free`, and
`google/gemini-2.0-flash-exp:free`. Expect free-tier rate limits — runs may be
slower or occasionally throttled.
```

- [ ] **Step 2: Update the `llm.py` row in the package CLAUDE.md**

In `src/productagents/CLAUDE.md`, find the `llm.py` row of the Layers table:

```
| `llm.py` | The single provider-agnostic `get_model()` factory. **Nodes never call this** — the model is injected into the graph and passed to each node via `partial`. |
```

Replace it with:

```
| `llm.py` | The single provider-agnostic `get_model()` factory. **Nodes never call this** — the model is injected into the graph and passed to each node via `partial`. An `openrouter:` model prefix routes through `langchain-openrouter` (`ChatOpenRouter`); the prefix is split on the first colon so a `:free` suffix survives. OpenRouter free models must support tool/function calling, since every node uses `with_structured_output`. |
```

- [ ] **Step 3: Verify the docs render and the suite is green**

Run: `uv run pytest`
Expected: full suite PASSES with coverage ≥ 90% (docs changes don't affect coverage; Tasks 1-2 added the covering tests).

- [ ] **Step 4: Commit**

```bash
git add README.md src/productagents/CLAUDE.md
git commit -m "docs: document OpenRouter free-model setup and tool-calling caveat

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K4CL9L3nUUqmh2bMp6Vwqn"
```

---

## Self-Review

**Spec coverage** — the request was "make the project support OpenRouter free models":
- Functional support → Task 1 (declare `langchain-openrouter`; `init_chat_model` and `setup.py` already handle the rest). ✅
- *Free* models specifically → Task 2 (free default) + Task 3 (how to set other free ids). ✅
- The one gotcha that would otherwise look like a silent failure (free models without tool calling → degraded output) → Task 3 docs + covered by the Global Constraints. ✅
- No node/graph/runner/TUI change is required because the model is injected and the colon-parsing already preserves `:free` — verified against `setup_screen.py` (writes only `PRODUCTAGENTS_MODEL` + key var, never `PRODUCTAGENTS_MODEL_PROVIDER`, so prefix parsing is never bypassed). ✅

**Placeholder scan** — every code/test/doc step contains the literal content to write; no TBD/TODO/"handle errors" placeholders. ✅

**Type consistency** — `ProviderInfo(label, key_var, default_model)` positional args in Task 2 match the dataclass in `setup.py:19-26`. The model id string `"openrouter:deepseek/deepseek-chat-v3-0324:free"` is identical across Task 1's test, Task 2's code + test, and Task 3's README. `model.model` is the verified attribute name on `ChatOpenRouter`. ✅
