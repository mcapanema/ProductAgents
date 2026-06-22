# OpenRouter Resilience & Degraded-Run Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the decision pipeline resilient to the transient/rate-limit errors that `:free` OpenRouter models throw, and stop the TUI from asking a human to approve a run whose core synthesis never happened.

**Architecture:** Two independent fixes. (1) **Resilience** — `get_model()` configures retries-with-backoff on the chat client, so a single transient upstream blip no longer becomes a hard node failure. (2) **Degraded-run handling** — the strategist's failure is made *detectable* (a `failed` flag on `Recommendation`), the graph **fails fast** to END when the recommendation is degraded (skipping judge/risk/governance/human-approval so it stops burning rate-limited calls and never reaches the dead-end interrupt), and the TUI then offers the human a **Retry / Make a decision anyway / Quit** choice instead of silently aborting. Failed runs are never auto-recorded.

**Tech Stack:** Python ≥ 3.14, LangChain 1.0 (`init_chat_model`), LangGraph 0.6 (`StateGraph`, conditional edges, `END`), Textual 4 (`ModalScreen`), Pydantic 2, pytest (offline, `FakeChatModel`).

## Global Constraints

- **Python ≥ 3.14**, managed with **uv** (`uv run pytest`, `uv run productagents`). Not Conda.
- **Nodes degrade, never crash** — every LLM call stays wrapped in `try/except Exception` with `# noqa: BLE001`, returning a fallback record. Do not remove existing degrade paths.
- **Model is injected, never constructed in a node** — only `llm.get_model()` builds a model; nodes receive it via `partial`.
- **Stream through `agents._stream.get_writer()`** in nodes, never `langgraph.config` directly.
- **Tests are fully offline** — no test may require an API key or hit the network. Use `tests/fakes.py::FakeChatModel` (maps a schema class → the instance or `Exception` its `with_structured_output(schema).ainvoke()` returns).
- **Coverage gate:** `--cov-fail-under=90` runs automatically with `uv run pytest`. Every new branch needs a test.
- **Lint:** ruff rule set in `pyproject.toml` (`BLE` is enabled — keep `# noqa: BLE001` on blind excepts). Line length 88.
- **Env-var reads go through `config.env_int` / `config.env_float`** (absence/parse-error/out-of-range → default).

---

## File Structure

| File | Change |
| --- | --- |
| `src/productagents/llm.py` | Modify — read `PRODUCTAGENTS_MAX_RETRIES`, pass `max_retries` to `init_chat_model`. |
| `src/productagents/schemas.py` | Modify — add `failed: bool = False` to `Recommendation`. |
| `src/productagents/agents/strategist.py` | Modify — set `failed=True` on the degrade fallback. |
| `src/productagents/graph.py` | Modify — add `_route_after_strategist`; make `strategist`'s outgoing edge conditional (`judge` or `END`). |
| `src/productagents/tui/degraded.py` | **Create** — `DegradedRunScreen` modal (Retry / Make a decision / Quit). |
| `src/productagents/tui/app.py` | Modify — `_on_finished` renders the failed state; `_run` records only non-failed runs and routes degraded runs to the new modal; extract a `_record` helper. |
| `.env.example` | Modify — document `PRODUCTAGENTS_MAX_RETRIES`. |
| `README.md` | Modify — document the retry knob + an OpenRouter reliability note. |
| `CLAUDE.md` (root) + `src/productagents/CLAUDE.md` | Modify — document the new env var and the fail-fast behavior. |
| `tests/test_llm.py` | Modify — assert `max_retries` is wired and configurable. |
| `tests/test_schemas.py` | Modify — assert `Recommendation.failed` defaults to `False`. |
| `tests/test_strategist.py` | Modify — assert the degrade path sets `failed=True`. |
| `tests/test_graph.py` | Modify — assert fail-fast: failed recommendation ends the run before judge/risk/governance, no interrupt. |
| `tests/test_env_example.py` | Modify — add the new key to `EXPECTED_KEYS`. |
| `tests/test_degraded_tui.py` | **Create** — the modal returns the chosen action. |
| `tests/test_tui.py` | Modify — degraded run shows modal (retry re-runs, decide records, quit records nothing); healthy run still records; failed run is not auto-recorded. |

---

## Task 1: Configurable retry/backoff in `get_model()` (Problem 1 fix)

The root cause of "analysts ran fine, everything after returned `Provider returned error`": `:free` OpenRouter models serve the first burst (5 parallel analysts) then throw transient upstream 429/5xx on subsequent calls. `get_model()` builds the client with **no retry configuration**, so one blip = a hard node failure. The failure tracks *timing*, not schema (the debate node uses the simplest schema in the system and still fails), which is why retries — not a schema change — are the fix. The OpenAI-compatible client honors `Retry-After`, so a bounded `max_retries` with backoff absorbs these.

**Files:**
- Modify: `src/productagents/llm.py`
- Test: `tests/test_llm.py`
- Docs: `.env.example`, `tests/test_env_example.py`, `README.md`, `CLAUDE.md`, `src/productagents/CLAUDE.md`

**Interfaces:**
- Consumes: `productagents.config.env_int(name, default, *, minimum)` (existing).
- Produces: `get_model()` unchanged signature; now constructs the model with `max_retries=` from env `PRODUCTAGENTS_MAX_RETRIES` (default `6`, minimum `0`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_llm.py`:

```python
def test_default_max_retries_passed(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.delenv("PRODUCTAGENTS_MODEL", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MAX_RETRIES", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["kwargs"]["max_retries"] == 6


def test_max_retries_env_override(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.delenv("PRODUCTAGENTS_MODEL", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.setenv("PRODUCTAGENTS_MAX_RETRIES", "10")
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["kwargs"]["max_retries"] == 10


def test_max_retries_passed_with_provider(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.setenv("PRODUCTAGENTS_MODEL", "gpt-5.5")
    monkeypatch.setenv("PRODUCTAGENTS_MODEL_PROVIDER", "openai")
    monkeypatch.delenv("PRODUCTAGENTS_MAX_RETRIES", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["kwargs"]["model_provider"] == "openai"
    assert captured["kwargs"]["max_retries"] == 6
```

Also update the two **existing** assertions in `tests/test_llm.py` that pin `captured["kwargs"]` to an exact dict, since `max_retries` is now always present:
- In `test_default_model_used_when_env_unset`: change `assert captured["kwargs"] == {}` to `assert captured["kwargs"] == {"max_retries": 6}`.
- In `test_env_overrides_model_and_provider`: change `assert captured["kwargs"] == {"model_provider": "openai"}` to `assert captured["kwargs"] == {"model_provider": "openai", "max_retries": 6}`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_llm.py -v`
Expected: the new tests FAIL (`KeyError: 'max_retries'`) and the two edited assertions FAIL (dict mismatch).

- [ ] **Step 3: Implement the retry config**

Replace the body of `src/productagents/llm.py` with:

```python
"""Provider-agnostic chat-model factory.

Every agent obtains its model through `get_model()` so the provider can be
swapped via configuration without touching agent code.
"""

import os

from langchain.chat_models import init_chat_model

from productagents.config import env_int

DEFAULT_MODEL = "anthropic:claude-sonnet-4-6"
# Free OpenRouter models throw transient upstream 429/5xx ("Provider returned
# error") under load; the underlying client honors Retry-After, so a bounded
# retry budget with backoff absorbs these without crashing a node.
DEFAULT_MAX_RETRIES = 6


def get_model():
    """Return a chat model selected by environment configuration.

    `PRODUCTAGENTS_MODEL` sets the model (default `DEFAULT_MODEL`). When given,
    `PRODUCTAGENTS_MODEL_PROVIDER` is passed through as `model_provider`.
    `PRODUCTAGENTS_MAX_RETRIES` (default 6) sets the client's automatic
    retry-with-backoff budget for transient provider errors.
    """
    model = os.environ.get("PRODUCTAGENTS_MODEL", DEFAULT_MODEL)
    provider = os.environ.get("PRODUCTAGENTS_MODEL_PROVIDER")
    max_retries = env_int("PRODUCTAGENTS_MAX_RETRIES", DEFAULT_MAX_RETRIES, minimum=0)
    if provider:
        return init_chat_model(
            model, model_provider=provider, max_retries=max_retries
        )
    return init_chat_model(model, max_retries=max_retries)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_llm.py -v`
Expected: PASS. (Note: `test_openrouter_free_model_resolves_to_chatopenrouter` constructs a real `ChatOpenRouter`, which accepts `max_retries` — it must still pass.)

- [ ] **Step 5: Document the env var**

In `.env.example`, append after the `PRODUCTAGENTS_DEBATE_ROUNDS` block:

```bash

# --- Resilience ---
# Automatic retry budget (with backoff) for transient provider errors such as
# free-tier OpenRouter "Provider returned error" 429/5xx responses. Default: 6
PRODUCTAGENTS_MAX_RETRIES="6"
```

In `tests/test_env_example.py`, add `"PRODUCTAGENTS_MAX_RETRIES",` to the `EXPECTED_KEYS` tuple.

In `README.md`, add to the env-var list (the block containing `PRODUCTAGENTS_JUDGE_MAX_RETRIES` near the other `export` lines):

```bash
export PRODUCTAGENTS_MAX_RETRIES=6      # retry budget (with backoff) for transient provider errors
```

And add a sentence to the OpenRouter section (the block with the `openrouter:deepseek/...:free` example):

```
> Free OpenRouter models are rate-limited and frequently return transient
> "Provider returned error" responses under load. `PRODUCTAGENTS_MAX_RETRIES`
> (default 6) retries these with backoff; if a model hits a hard daily cap,
> switch to a keyed/paid model.
```

In `src/productagents/CLAUDE.md`, in the `llm.py` row of the Layers table, append:
`` `PRODUCTAGENTS_MAX_RETRIES` (default 6) sets the client's retry-with-backoff budget for transient provider errors.``

In root `CLAUDE.md`, under "Runtime configuration (env vars)", add a bullet:
`- `PRODUCTAGENTS_MAX_RETRIES` — automatic retry budget (with backoff) for transient provider errors (e.g. free-tier OpenRouter 429/5xx), default 6.`

- [ ] **Step 6: Run the full doc-guarded suite**

Run: `uv run pytest tests/test_llm.py tests/test_env_example.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/productagents/llm.py tests/test_llm.py .env.example tests/test_env_example.py README.md CLAUDE.md src/productagents/CLAUDE.md
git commit -m "feat(llm): configurable retry-with-backoff for transient provider errors"
```

---

## Task 2: Make a failed recommendation detectable

The strategist's degrade path emits a zero-confidence placeholder `Recommendation`, but nothing downstream can tell it apart from a real one because `Recommendation` has no failure flag. Add one.

**Files:**
- Modify: `src/productagents/schemas.py:104-110` (the `Recommendation` model)
- Modify: `src/productagents/agents/strategist.py:80-85` (the degrade fallback)
- Test: `tests/test_schemas.py`, `tests/test_strategist.py`

**Interfaces:**
- Produces: `Recommendation.failed: bool` (default `False`). Real recommendations leave it `False`; the strategist's degrade fallback sets it `True`. Consumed by Task 3 (graph routing) and Task 5 (TUI recording/rendering).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_schemas.py`:

```python
from productagents.schemas import Recommendation


def test_recommendation_failed_defaults_false():
    rec = Recommendation(
        recommendation="ship it",
        confidence=0.9,
        rationale="strong demand",
        expected_outcomes=["growth"],
    )
    assert rec.failed is False
```

In `tests/test_strategist.py`, locate the existing degrade-path test (the one that maps `Recommendation` to an `Exception` and asserts confidence is 0.0). Add to its assertions:

```python
    assert result["recommendation"].failed is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_schemas.py::test_recommendation_failed_defaults_false tests/test_strategist.py -v`
Expected: FAIL (`AttributeError`/validation: no `failed` field; degrade test fails its new assertion).

- [ ] **Step 3: Add the flag and set it on degrade**

In `src/productagents/schemas.py`, change the `Recommendation` model to:

```python
class Recommendation(BaseModel):
    """The strategist's decision proposal."""

    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    expected_outcomes: list[str]
    failed: bool = False
```

In `src/productagents/agents/strategist.py`, in the `except` block, set `failed=True`:

```python
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "error": str(exc)})
        recommendation = Recommendation(
            recommendation="Unable to produce a recommendation due to an error.",
            confidence=0.0,
            rationale=f"Strategist failed: {exc}",
            expected_outcomes=[],
            failed=True,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_schemas.py tests/test_strategist.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/schemas.py src/productagents/agents/strategist.py tests/test_schemas.py tests/test_strategist.py
git commit -m "feat(schemas): add failed flag to Recommendation; strategist sets it on degrade"
```

---

## Task 3: Graph fails fast when the recommendation failed

When the strategist can't synthesize a recommendation, running judge → risk → governance → human_approval is pointless: it burns more rate-limited calls and ends at a dead-end human prompt. Route `strategist → END` in that case.

**Files:**
- Modify: `src/productagents/graph.py:51-58` (add `_route_after_strategist`) and `:94` (replace the plain `strategist → judge` edge with a conditional edge)
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: `Recommendation.failed` (Task 2), `END` (already imported from `langgraph.graph`).
- Produces: `_route_after_strategist(state) -> str` returning `"judge"` when the recommendation is present and not failed, else `END`. Wired via `add_conditional_edges("strategist", _route_after_strategist, {"judge": "judge", END: END})`. Effect: a failed strategist ends the run before judge/risk/governance, so no `__interrupt__` is ever raised on a degraded run.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_graph.py` (mirror the existing graph tests' style — build with `FakeChatModel`, drive via `run_decision`):

```python
import pytest

from productagents.graph import build_graph
from productagents.runner import (
    FinishedEvent,
    GovernanceVerdictEvent,
    JudgmentEvent,
    RiskAssessmentEvent,
    run_decision,
)
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    Initiative,
    Recommendation,
)
from tests.fakes import FakeChatModel


@pytest.fixture
def _failed_strategist_model():
    return FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: RuntimeError("Provider returned error"),
        }
    )


async def test_failed_recommendation_ends_run_before_governance(
    _failed_strategist_model, monkeypatch
):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = build_graph(_failed_strategist_model, human_in_the_loop=True)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    initiative = Initiative(title="SSO", description="SSO")

    events = [
        e
        async for e in run_decision(graph, initiative, evidence)
    ]

    # No judge, risk, or governance events: the run fails fast at the strategist.
    assert not any(isinstance(e, JudgmentEvent) for e in events)
    assert not any(isinstance(e, RiskAssessmentEvent) for e in events)
    assert not any(isinstance(e, GovernanceVerdictEvent) for e in events)
    finished = next(e for e in events if isinstance(e, FinishedEvent))
    assert finished.recommendation is not None
    assert finished.recommendation.failed is True
    assert finished.governance is None
```

Note: `run_decision` is called **without** an `approver`. If fail-fast is not yet wired, the graph reaches `human_approval`, raises `__interrupt__`, and the no-approver branch auto-approves — producing a `FinalVerdictEvent` and a non-None governance. The assertions above therefore fail until the conditional edge is added.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_graph.py::test_failed_recommendation_ends_run_before_governance -v`
Expected: FAIL (governance/judgment events present; `finished.governance` not None).

- [ ] **Step 3: Add the routing function and conditional edge**

In `src/productagents/graph.py`, add this function next to `_route_after_judge`:

```python
def _route_after_strategist(state) -> str:
    """Fail fast: end the run when the strategist could not produce a rec."""
    recommendation = state.get("recommendation")
    if recommendation is None or recommendation.failed:
        return END
    return "judge"
```

Then replace the plain edge:

```python
    graph.add_edge("debate", "strategist")
    graph.add_edge("strategist", "judge")
```

with:

```python
    graph.add_edge("debate", "strategist")
    graph.add_conditional_edges(
        "strategist",
        _route_after_strategist,
        {"judge": "judge", END: END},
    )
```

(Leave the existing `judge → (strategist|risk)` conditional edge and all later edges unchanged.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_graph.py::test_failed_recommendation_ends_run_before_governance -v`
Expected: PASS.

- [ ] **Step 5: Run the full graph + runner suite (no regressions on healthy runs)**

Run: `uv run pytest tests/test_graph.py tests/test_runner.py -v`
Expected: PASS — healthy runs (real `Recommendation`) still flow through judge/risk/governance.

- [ ] **Step 6: Commit**

```bash
git add src/productagents/graph.py tests/test_graph.py
git commit -m "feat(graph): fail fast to END when the strategist cannot produce a recommendation"
```

---

## Task 4: `DegradedRunScreen` modal (Retry / Make a decision / Quit)

When a run fails fast, the TUI should not silently abort — it should let the human choose what to do. This task builds the modal in isolation.

**Files:**
- Create: `src/productagents/tui/degraded.py`
- Test: `tests/test_degraded_tui.py`

**Interfaces:**
- Produces: `DegradedRunScreen(ModalScreen[str])`. Dismisses with one of the literals `"retry"`, `"decide"`, `"quit"` (the pressed button's id). Consumed by Task 5.

- [ ] **Step 1: Write the failing test**

Create `tests/test_degraded_tui.py`:

```python
from textual.app import App

from productagents.tui.degraded import DegradedRunScreen


class _Harness(App):
    def __init__(self):
        super().__init__()
        self.result = None

    async def on_mount(self):
        self.result = await self.push_screen_wait(DegradedRunScreen())


async def test_retry_button_returns_retry():
    app = _Harness()
    async with app.run_test() as pilot:
        await pilot.click("#retry")
        await pilot.pause()
    assert app.result == "retry"


async def test_decide_button_returns_decide():
    app = _Harness()
    async with app.run_test() as pilot:
        await pilot.click("#decide")
        await pilot.pause()
    assert app.result == "decide"


async def test_quit_button_returns_quit():
    app = _Harness()
    async with app.run_test() as pilot:
        await pilot.click("#quit")
        await pilot.pause()
    assert app.result == "quit"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_degraded_tui.py -v`
Expected: FAIL (`ModuleNotFoundError: productagents.tui.degraded`).

- [ ] **Step 3: Implement the modal**

Create `src/productagents/tui/degraded.py`:

```python
"""Degraded-run prompt: the pipeline could not produce a recommendation.

Shown when a decision run fails fast because the strategist could not synthesize
a recommendation (typically a cascade of transient provider errors). Rather than
silently aborting or forcing an uninformed approval, the human chooses how to
proceed; the pressed button's id is returned via `Screen.dismiss`.
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class DegradedRunScreen(ModalScreen[str]):
    """Offer Retry / Make a decision anyway / Quit for a degraded run."""

    def compose(self) -> ComposeResult:
        yield Static(
            "This run could not produce a recommendation — the pipeline hit "
            "provider errors before synthesizing a decision. See Status / Errors "
            "for details.\n\nWhat would you like to do?",
            id="degraded-message",
        )
        yield Button("Retry the run", id="retry", variant="primary")
        yield Button("Make a decision anyway", id="decide")
        yield Button("Quit (discard)", id="quit", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_degraded_tui.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/tui/degraded.py tests/test_degraded_tui.py
git commit -m "feat(tui): add DegradedRunScreen modal (retry/decide/quit)"
```

---

## Task 5: Wire degraded handling and the recording rule into the app

Final integration: render the failed strategist state, never auto-record a failed run, and on a degraded run present `DegradedRunScreen` — Retry re-runs, "Make a decision anyway" opens the existing `ApprovalScreen` and records the human's decision, Quit discards.

**Files:**
- Modify: `src/productagents/tui/app.py` — imports; `_on_finished` (`:425-428`); the `_run` tail (`:348-362`); add `_record` and `_handle_degraded` helpers.
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `DegradedRunScreen` (Task 4), `Recommendation.failed` (Task 2), existing `ApprovalScreen`, `self._ask_human`, `self._recorder`, `self._reset_panels`.
- Produces (recording rule): a run is auto-recorded **only** when `finished.recommendation is not None and not finished.recommendation.failed`. On the "decide" path the human's deliberate choice **is** recorded (a real human decision), with the degraded recommendation preserved and `governance.decided_by="human"`. Quit and dismissed-modal record nothing.

- [ ] **Step 1: Write the failing tests**

In `tests/test_tui.py`, add tests that drive the worker with a fake runner. Use this helper pattern (mirror the existing tests' construction of `ProductAgentsApp` with injected seams; if a similar async-generator fake runner already exists in the file, reuse it):

```python
from productagents.runner import FinishedEvent
from productagents.schemas import (
    GovernanceVerdict,
    HumanDecision,
    Initiative,
    Recommendation,
)
from productagents.tui.app import ProductAgentsApp
from productagents.tui.degraded import DegradedRunScreen


def _evidence():
    from productagents.schemas import Evidence

    return Evidence(
        scenario="sample", customer_feedback="x", product_analytics={"a": 1}
    )


def _failed_finished():
    rec = Recommendation(
        recommendation="Unable to produce a recommendation due to an error.",
        confidence=0.0,
        rationale="Strategist failed: boom",
        expected_outcomes=[],
        failed=True,
    )
    return FinishedEvent(
        recommendation=rec, reports=[], debate=[], risks=[], governance=None
    )


def _ok_finished():
    rec = Recommendation(
        recommendation="Build SSO",
        confidence=0.8,
        rationale="demand",
        expected_outcomes=["growth"],
    )
    return FinishedEvent(
        recommendation=rec, reports=[], debate=[], risks=[], governance=None
    )


def _runner_yielding(*events):
    async def _runner(initiative, evidence, *, portfolio=None, outcomes=None, approver=None):
        for e in events:
            yield e

    return _runner


async def test_failed_run_is_not_auto_recorded_and_shows_modal(monkeypatch):
    recorded = []
    chosen = {}

    app = ProductAgentsApp(
        _runner_yielding(_failed_finished()),
        _evidence(),
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async def fake_push_screen_wait(screen):
        chosen["screen"] = type(screen).__name__
        return "quit"

    async with app.run_test() as pilot:
        monkeypatch.setattr(app, "push_screen_wait", fake_push_screen_wait)
        app._run(Initiative(title="SSO", description="SSO"), _evidence())
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()

    assert chosen["screen"] == "DegradedRunScreen"
    assert recorded == []  # quit records nothing


async def test_decide_path_records_human_decision(monkeypatch):
    recorded = []

    app = ProductAgentsApp(
        _runner_yielding(_failed_finished()),
        _evidence(),
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async def fake_push_screen_wait(screen):
        if isinstance(screen, DegradedRunScreen):
            return "decide"
        return HumanDecision(verdict="reject", rationale="not now")

    async with app.run_test() as pilot:
        monkeypatch.setattr(app, "push_screen_wait", fake_push_screen_wait)
        app._run(Initiative(title="SSO", description="SSO"), _evidence())
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()

    assert len(recorded) == 1
    record = recorded[0]
    assert record.governance.verdict == "reject"
    assert record.governance.decided_by == "human"


async def test_healthy_run_is_recorded(monkeypatch):
    recorded = []

    app = ProductAgentsApp(
        _runner_yielding(_ok_finished()),
        _evidence(),
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        app._run(Initiative(title="SSO", description="SSO"), _evidence())
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO"
```

(If `tests/test_tui.py` already defines equivalent helpers for building a fake runner / evidence / app, reuse them instead of redefining — DRY. Keep only the three `test_*` functions.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_tui.py -k "failed_run or decide_path or healthy_run" -v`
Expected: FAIL (no `DegradedRunScreen` shown; failed run still recorded).

- [ ] **Step 3: Update imports**

In `src/productagents/tui/app.py`, add to the schema import (it currently imports `DecisionRecord, Initiative`):

```python
from productagents.schemas import DecisionRecord, GovernanceVerdict, Initiative
```

And add the new screen import alongside the other `tui` imports:

```python
from productagents.tui.degraded import DegradedRunScreen
```

- [ ] **Step 4: Render the failed strategist state**

Replace `_on_finished` (`src/productagents/tui/app.py:425-428`) with:

```python
    def _on_finished(self, event) -> None:
        rec = event.recommendation
        if rec is None:
            return
        if rec.failed:
            self.query_one("#strategist", Static).update(
                "[red]failed — could not synthesize a recommendation. "
                "See Status / Errors below.[/red]"
            )
            self._set_state("strategist", "failed")
            return
        self._render_recommendation(rec)
        self._set_state("strategist", "done")
```

- [ ] **Step 5: Extract `_record` and route the `_run` tail**

Replace the tail of `_run` (`src/productagents/tui/app.py:348-362`, the `if finished is not None and finished.recommendation is not None:` block) with:

```python
        if finished is None or finished.recommendation is None:
            return
        if not finished.recommendation.failed:
            self._record(initiative, evidence, finished)
            return
        await self._handle_degraded(initiative, evidence, finished)
```

Then add these three methods to `ProductAgentsApp` (place them just after `_run`):

```python
    def _record(self, initiative, evidence, finished, *, governance=None) -> None:
        self._recorder(
            DecisionRecord(
                initiative=initiative,
                recommendation=finished.recommendation,
                reports=finished.reports,
                debate=finished.debate,
                risks=finished.risks,
                governance=governance
                if governance is not None
                else finished.governance,
                judgment=finished.judgment,
                prior_lessons=finished.prior_lessons,
                evidence_sources=evidence.sources,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

    async def _handle_degraded(self, initiative, evidence, finished) -> None:
        choice = await self.push_screen_wait(DegradedRunScreen())
        if choice == "retry":
            self._reset_panels()
            self._run(initiative, evidence)
        elif choice == "decide":
            decision = await self._ask_human(None)
            governance = GovernanceVerdict(
                verdict=decision.verdict,
                rationale=decision.rationale,
                decided_by="human",
            )
            self._record(initiative, evidence, finished, governance=governance)
        # "quit" or dismissed: record nothing, leave the failed panels in place.
```

- [ ] **Step 6: Run the new TUI tests to verify they pass**

Run: `uv run pytest tests/test_tui.py -k "failed_run or decide_path or healthy_run" -v`
Expected: PASS.

- [ ] **Step 7: Run the entire suite + coverage gate**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%. If any pre-existing TUI test asserted that a failed/zero-confidence run was recorded, update it to the new contract (failed runs are not auto-recorded).

- [ ] **Step 8: Lint and type-check**

Run: `uv run ruff check src tests && uv run ruff format --check src tests`
Expected: clean. (If `ty` is part of the project's checks: `uv run ty check`.)

- [ ] **Step 9: Update the graph update artifact and commit**

```bash
graphify update .
git add src/productagents/tui/app.py tests/test_tui.py graphify-out
git commit -m "feat(tui): offer retry/decide/quit on a degraded run; never auto-record failed runs"
```

---

## Manual verification (run the app)

After all tasks, to confirm end-to-end with a real key, run `uv run productagents`, configure an OpenRouter `:free` model, and start a decision. Expected: transient errors are retried (fewer node failures); if the strategist still can't produce a recommendation, the run ends at the strategist panel and the **Retry / Make a decision anyway / Quit** modal appears instead of the Portfolio Manager approval prompt. (Optional — not part of the offline suite.)

---

## Self-Review

**Spec coverage:**
- "Advocate/Skeptic/Strategist/Judge/Portfolio Manager returned error while analysts ran fine" → root-caused (transient `:free` errors, no retry) and fixed in **Task 1** (retry-with-backoff). The root-cause reasoning (timing not schema — debate uses the simplest schema and still failed) is captured in Task 1's preamble.
- "Workflow continued and prompted me to Approve/Reject/Request Analysis with no information" → **Task 2** (detect failed rec) + **Task 3** (fail fast to END, so the human prompt is never reached on a degraded run) + **Task 5** (offer Retry/Decide/Quit instead).
- User's chosen behaviors: *fail fast then ask the user (retry / make a decision / quit)* → Tasks 3 + 4 + 5; *don't record failed runs* → Task 5's recording rule.

**Placeholder scan:** No TBD/"handle errors"/"similar to" — every code step has complete code. Degrade paths preserved with `# noqa: BLE001`.

**Type consistency:** `Recommendation.failed: bool` defined in Task 2 and consumed by the same name in Tasks 3 (`recommendation.failed`) and 5 (`finished.recommendation.failed`). `_route_after_strategist` returns `"judge"` / `END`, matching the path map `{"judge": "judge", END: END}`. `DegradedRunScreen` returns `"retry"/"decide"/"quit"`, matched verbatim in `_handle_degraded`. `_record(..., *, governance=None)` signature matches both call sites.

**Open follow-up (out of scope, flagged for the user):** on the "Make a decision anyway" path the recorded `DecisionRecord` still carries `recommendation.failed=True`, so a future `recall` could surface it. If that becomes noise, add a `failed`-record filter in `memory.select_relevant_lessons` / `read_decisions` — a small, separate change.
