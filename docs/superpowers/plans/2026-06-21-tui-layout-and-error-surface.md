# TUI Layout Redesign & Error Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the linear, single-column ProductAgents TUI with a multi-lane (3-column) layout that includes an analyst grid, add a persistent "Status / Errors" panel that surfaces node failures (e.g. API rate limits) which are currently swallowed silently, and apply a cohesive theme with per-stage accent colors and status icons.

**Architecture:** Errors already exist inside the graph — every node degrades on exception and emits a `status: "failed: …"` progress chunk, but the runner collapses those into generic `ProgressEvent`s and the TUI's `NodeCompleteEvent` handler then overwrites the panel with `(no findings)`, erasing the error. We fix this end-to-end: nodes emit an explicit `{"node", "error"}` custom chunk on degradation → the runner translates it into a new `NodeErrorEvent` → the TUI logs it to a docked Status/Errors panel and marks the failing panel `✗ FAILED`. The layout work is pure `compose()` + `app.tcss` restructuring into a left/center/right `Horizontal` with a 3×2 analyst `Grid`. The polish pass registers a Textual `Theme` and adds per-stage accent borders and `·/●/✓/✗` state icons in panel titles.

**Tech Stack:** Python ≥3.14, uv, Textual 8.2.7 (`textual.containers.Grid`/`Vertical`/`Horizontal`/`VerticalScroll`, `textual.theme.Theme`), LangGraph, Pydantic, pytest (offline, `FakeChatModel`).

## Global Constraints

- Python ≥ 3.14; manage everything with **uv** (`uv run pytest`, `uv run productagents`).
- Tests run **fully offline** — no API key, no network. Use `tests/fakes.py::FakeChatModel` (maps a schema class → the instance, or an `Exception` to exercise the degrade path).
- Coverage gate is enforced: `--cov-fail-under=90` (configured in `pyproject.toml`). Every new branch needs a test.
- `asyncio_mode = "auto"` — write `async def test_*` with **no** decorator.
- **Nodes degrade, never crash.** Keep every node's `try/except Exception` (`# noqa: BLE001`) fallback. We are *adding* an error emission inside the existing `except`, not changing the fallback record.
- **Stream from nodes only via `agents._stream.get_writer()`** (never `langgraph.config.get_stream_writer()` directly).
- Textual exact version is **8.2.7**. `Grid`, `Vertical`, `Horizontal`, `VerticalScroll` come from `textual.containers`; `Theme` from `textual.theme`; `NoMatches` from `textual.css.query`.
- After code changes that touch `src/`, run `graphify update .` to keep the graph current (no API cost).

---

## File Structure

| File | Change | Responsibility |
| --- | --- | --- |
| `src/productagents/runner.py` | Modify | Add `NodeErrorEvent` dataclass; translate `{"node","error"}` custom chunks into it. |
| `src/productagents/agents/_analyst.py` | Modify | Emit `{"node", "error"}` on degradation (replaces the `status: "failed: …"` emit). |
| `src/productagents/agents/debate.py` | Modify | Emit `{"node","error"}` when a turn fails. |
| `src/productagents/agents/risk.py` | Modify | Emit `{"node","error"}` when a reviewer fails. |
| `src/productagents/agents/strategist.py` | Modify | Emit `{"node","error"}` on degradation. |
| `src/productagents/agents/governance.py` | Modify | Emit `{"node","error"}` on degradation. |
| `src/productagents/tui/app.py` | Modify | Status/Errors panel, `NodeErrorEvent` handling, failed badges, 3-lane layout, theme + state icons. |
| `src/productagents/tui/app.tcss` | Modify | Lane/grid layout, docked status panel, per-stage accents, `.failed` styling. |
| `tests/test_runner.py` | Modify | Tests for `NodeErrorEvent` emission per node. |
| `tests/test_tui.py` | Modify | Tests for status panel, failed badge, lane containers, state icons; update 2 existing tests that asserted errors land in `#strategist`. |

---

### Task 1: Runner `NodeErrorEvent` + analysts report the real error

**Files:**
- Modify: `src/productagents/runner.py`
- Modify: `src/productagents/agents/_analyst.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Produces: `runner.NodeErrorEvent(node: str, message: str)` (frozen dataclass like the others). Emitted whenever a custom chunk contains an `"error"` key. Later tasks (TUI) consume it.
- Consumes: the `get_writer()` callable each node already holds.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_runner.py` (keep existing imports; add `NodeErrorEvent` to the `runner` import and the schema imports shown):

```python
async def test_runner_emits_node_error_when_analyst_degrades(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.graph import build_graph
    from productagents.runner import NodeErrorEvent, run_decision
    from productagents.schemas import (
        AnalystFindings,
        DebateArgument,
        Evidence,
        GovernanceFinding,
        Initiative,
        Recommendation,
        RiskFinding,
    )
    from tests.fakes import FakeChatModel

    model = FakeChatModel(
        {
            AnalystFindings: RuntimeError("429 Too Many Requests: rate limit reached"),
            DebateArgument: DebateArgument(argument="a"),
            Recommendation: Recommendation(
                recommendation="r", confidence=0.5, rationale="x", expected_outcomes=["o"]
            ),
            RiskFinding: RiskFinding(level="low", rationale="ok"),
            GovernanceFinding: GovernanceFinding(verdict="approve", rationale="ok"),
        }
    )
    graph = build_graph(model)
    evidence = Evidence(
        scenario="s", customer_feedback="d", product_analytics={"x": 1}
    )

    events = []
    async for event in run_decision(
        graph, Initiative(title="t", description="d"), evidence
    ):
        events.append(event)

    errors = [e for e in events if isinstance(e, NodeErrorEvent)]
    analyst_ids = {
        "customer_research",
        "product_analytics",
        "market",
        "business",
        "technical",
    }
    assert errors, "expected NodeErrorEvent(s) for the failing analysts"
    assert all(e.node in analyst_ids for e in errors)
    assert any("429" in e.message for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_runner.py::test_runner_emits_node_error_when_analyst_degrades -x`
Expected: FAIL with `ImportError: cannot import name 'NodeErrorEvent'`.

- [ ] **Step 3a: Add the `NodeErrorEvent` dataclass to `runner.py`**

In `src/productagents/runner.py`, add after the `GovernanceVerdictEvent` dataclass (around line 54):

```python
@dataclass
class NodeErrorEvent:
    node: str
    message: str
```

Add `NodeErrorEvent` to the `AsyncIterator[...]` union in `run_decision`'s return annotation (insert `| NodeErrorEvent` after `GovernanceVerdictEvent`).

- [ ] **Step 3b: Recognize the `error` custom chunk in `run_decision`**

In `src/productagents/runner.py`, inside the `if mode == "custom":` branch, add a new `elif` **before** the final `else:` that yields `ProgressEvent`:

```python
                elif "error" in chunk:
                    yield NodeErrorEvent(
                        node=chunk.get("node", ""), message=chunk["error"]
                    )
```

- [ ] **Step 3c: Make analysts emit the error chunk**

In `src/productagents/agents/_analyst.py`, replace the `except` body's writer line:

```python
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": analyst_id, "status": f"failed: {exc}"})
```

with:

```python
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": analyst_id, "error": str(exc)})
```

(The `failed=True` report return below it is unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_runner.py::test_runner_emits_node_error_when_analyst_degrades -x`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/runner.py src/productagents/agents/_analyst.py tests/test_runner.py
git commit -m "feat: surface analyst failures as NodeErrorEvent"
```

---

### Task 2: Remaining nodes emit error chunks on degradation

**Files:**
- Modify: `src/productagents/agents/debate.py`
- Modify: `src/productagents/agents/risk.py`
- Modify: `src/productagents/agents/strategist.py`
- Modify: `src/productagents/agents/governance.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `NodeErrorEvent` from Task 1.
- Produces: `NodeErrorEvent(node="debate" | "risk" | "strategist" | "governance", message=str(exc))` when those nodes degrade.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_runner.py`. These reuse the graph-driving pattern from Task 1's test; each maps one schema to an `Exception` so exactly one node degrades:

```python
async def _drive_with(model, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.graph import build_graph
    from productagents.runner import run_decision
    from productagents.schemas import Evidence, Initiative

    graph = build_graph(model)
    evidence = Evidence(scenario="s", customer_feedback="d", product_analytics={"x": 1})
    events = []
    async for event in run_decision(
        graph, Initiative(title="t", description="d"), evidence
    ):
        events.append(event)
    return events


def _base_results():
    from productagents.schemas import (
        AnalystFindings,
        DebateArgument,
        GovernanceFinding,
        Recommendation,
        RiskFinding,
    )

    return {
        AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
        DebateArgument: DebateArgument(argument="a"),
        Recommendation: Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=["o"]
        ),
        RiskFinding: RiskFinding(level="low", rationale="ok"),
        GovernanceFinding: GovernanceFinding(verdict="approve", rationale="ok"),
    }


async def test_runner_emits_node_error_for_debate(monkeypatch):
    from productagents.runner import NodeErrorEvent
    from productagents.schemas import DebateArgument
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[DebateArgument] = RuntimeError("debate boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(
        isinstance(e, NodeErrorEvent) and e.node == "debate" for e in events
    )


async def test_runner_emits_node_error_for_risk(monkeypatch):
    from productagents.runner import NodeErrorEvent
    from productagents.schemas import RiskFinding
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[RiskFinding] = RuntimeError("risk boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(isinstance(e, NodeErrorEvent) and e.node == "risk" for e in events)


async def test_runner_emits_node_error_for_strategist(monkeypatch):
    from productagents.runner import NodeErrorEvent
    from productagents.schemas import Recommendation
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[Recommendation] = RuntimeError("strategist boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(
        isinstance(e, NodeErrorEvent) and e.node == "strategist" for e in events
    )


async def test_runner_emits_node_error_for_governance(monkeypatch):
    from productagents.runner import NodeErrorEvent
    from productagents.schemas import GovernanceFinding
    from tests.fakes import FakeChatModel

    results = _base_results()
    results[GovernanceFinding] = RuntimeError("governance boom")
    events = await _drive_with(FakeChatModel(results), monkeypatch)
    assert any(
        isinstance(e, NodeErrorEvent) and e.node == "governance" for e in events
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_runner.py -k node_error -x`
Expected: the four new node-specific tests FAIL (no error chunk emitted by those nodes yet); Task 1's analyst test still passes.

- [ ] **Step 3a: `debate.py` — emit error chunk per failed turn**

In `src/productagents/agents/debate.py`, replace the turn `except` block:

```python
            except Exception as exc:  # noqa: BLE001 - degrade one turn, never crash
                argument = f"({side} unavailable: {exc})"
```

with:

```python
            except Exception as exc:  # noqa: BLE001 - degrade one turn, never crash
                writer({"node": NODE_ID, "error": str(exc)})
                argument = f"({side} unavailable: {exc})"
```

- [ ] **Step 3b: `risk.py` — emit error chunk per failed reviewer**

In `src/productagents/agents/risk.py`, replace the reviewer `except` block opening:

```python
        except Exception as exc:  # noqa: BLE001 - degrade one reviewer, never crash
            assessment = RiskAssessment(
```

with:

```python
        except Exception as exc:  # noqa: BLE001 - degrade one reviewer, never crash
            writer({"node": NODE_ID, "error": str(exc)})
            assessment = RiskAssessment(
```

- [ ] **Step 3c: `strategist.py` — emit error chunk**

In `src/productagents/agents/strategist.py`, replace:

```python
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "status": f"failed: {exc}"})
```

with:

```python
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "error": str(exc)})
```

- [ ] **Step 3d: `governance.py` — emit error chunk**

In `src/productagents/agents/governance.py`, replace:

```python
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "status": f"failed: {exc}"})
```

with:

```python
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "error": str(exc)})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_runner.py -k node_error`
Expected: all five `node_error` tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/debate.py src/productagents/agents/risk.py \
        src/productagents/agents/strategist.py src/productagents/agents/governance.py \
        tests/test_runner.py
git commit -m "feat: emit error chunks from debate, risk, strategist, governance nodes"
```

---

### Task 3: Status/Errors panel, failed badges, and error routing in the TUI

**Files:**
- Modify: `src/productagents/tui/app.py`
- Modify: `src/productagents/tui/app.tcss`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `runner.NodeErrorEvent`.
- Produces (within `app.py`, used by Task 5): module dict `_TITLES: dict[str, str]` (widget-id → base border title), module dict `_WIDGET_FOR_NODE: dict[str, str]` (runner node name → widget id), methods `_log_status(self, message: str, *, level: str = "info") -> None` and `_mark_failed(self, node: str) -> None`. The new widget has `id="status-log"`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tui.py`:

```python
async def test_app_logs_node_error_and_marks_panel_failed():
    from productagents.runner import FinishedEvent, NodeErrorEvent
    from productagents.schemas import Evidence, Recommendation

    async def fake_runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        yield NodeErrorEvent(node="technical", message="429 rate limit reached")
        yield FinishedEvent(
            recommendation=Recommendation(
                recommendation="Build it",
                confidence=0.5,
                rationale="r",
                expected_outcomes=["o"],
            ),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
        )

    evidence = Evidence(
        scenario="sample", customer_feedback="d", product_analytics={"x": 1}
    )
    app = ProductAgentsApp(
        fake_runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        status_text = str(pilot.app.query_one("#status-log").content)
        assert "429 rate limit reached" in status_text
        assert pilot.app.query_one("#technical").has_class("failed")
```

Then **update the two existing tests** that asserted errors land in `#strategist`:

In `test_app_shows_error_for_bad_evidence_source`, replace its final two lines:

```python
        strat_text = str(pilot.app.query_one("#strategist").content)

    assert ran["called"] is False
    assert "Evidence" in strat_text or "evidence" in strat_text
```

with:

```python
        status_text = str(pilot.app.query_one("#status-log").content)

    assert ran["called"] is False
    assert "Evidence" in status_text or "evidence" in status_text
```

In `test_app_surfaces_runner_unavailable`, replace its final two lines:

```python
        strat_text = str(pilot.app.query_one("#strategist").content)

    assert "langchain-google-genai" in strat_text
```

with:

```python
        status_text = str(pilot.app.query_one("#status-log").content)

    assert "langchain-google-genai" in status_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tui.py -k "node_error or bad_evidence or runner_unavailable" -x`
Expected: FAIL — `#status-log` does not exist yet / errors still go to `#strategist`.

- [ ] **Step 3a: Add the title/widget maps and import in `app.py`**

In `src/productagents/tui/app.py`, add the import near the other Textual imports:

```python
from textual.css.query import NoMatches
```

After the existing `_PANELS = {...}` dict, add:

```python
_TITLES = {
    "customer_research": "Customer Research Analyst",
    "product_analytics": "Product Analytics Analyst",
    "market": "Market Analyst",
    "business": "Business Analyst",
    "technical": "Technical Analyst",
    "recall": "Lessons from Past Decisions",
    "strategist": "Product Strategist",
    "evidence-provenance": "Evidence Sources",
    "debate-scroll": "Advocate vs Skeptic Debate",
    "risk-scroll": "Risk Team",
    "governance": "Portfolio Manager (Governance)",
    "status-log": "Status / Errors",
}

# Runner node names whose live widget differs from the node id.
_WIDGET_FOR_NODE = {
    "debate": "debate-scroll",
    "risk": "risk-scroll",
}
```

- [ ] **Step 3b: Add the status-log widget to `compose()`**

In `compose()`, add a status panel just before `yield Footer()`:

```python
        yield Static("", id="status-log", classes="panel")
        yield Footer()
```

- [ ] **Step 3c: Initialize status state in `__init__`**

In `ProductAgentsApp.__init__`, after `self._risk_lines: list[str] = []`, add:

```python
        self._status_lines: list[str] = []
```

- [ ] **Step 3d: Set all border titles from `_TITLES` in `on_mount`**

Replace the title-setting block in `on_mount` (the loop over `_PANELS` plus the four explicit `border_title` assignments) with:

```python
        for widget_id, title in _TITLES.items():
            self.query_one(f"#{widget_id}").border_title = title
        if self._show_home:
            self._open_home()
```

- [ ] **Step 3e: Add `_log_status` and `_mark_failed` helpers**

Add these methods to `ProductAgentsApp` (e.g. just after `_render_recommendation`):

```python
    def _log_status(self, message: str, *, level: str = "info") -> None:
        ts = datetime.now(UTC).strftime("%H:%M:%S")
        icon = "✗" if level == "error" else "·"
        color = "red" if level == "error" else "dim"
        self._status_lines.append(f"[{color}]{icon} {ts} {message}[/{color}]")
        self._status_lines = self._status_lines[-50:]
        self.query_one("#status-log", Static).update("\n".join(self._status_lines))

    def _mark_failed(self, node: str) -> None:
        widget_id = _WIDGET_FOR_NODE.get(node, node)
        try:
            panel = self.query_one(f"#{widget_id}")
        except NoMatches:
            return
        panel.add_class("failed")
        panel.styles.border = ("round", "red")
        base = _TITLES.get(widget_id)
        if base:
            panel.border_title = f"✗ {base}"
```

- [ ] **Step 3f: Handle `NodeErrorEvent` in the event loop**

Add `NodeErrorEvent` to the runner import in `app.py`, then in `_run`'s `async for` dispatch add a branch (place it near the other `isinstance` checks):

```python
            elif isinstance(event, NodeErrorEvent):
                label = _TITLES.get(_WIDGET_FOR_NODE.get(event.node, event.node), event.node)
                self._log_status(f"{label}: {event.message}", level="error")
                self._mark_failed(event.node)
```

- [ ] **Step 3g: Don't let a failed analyst's `(no findings)` erase context**

In the `NodeCompleteEvent` branch of `_run`, replace:

```python
            elif isinstance(event, NodeCompleteEvent):
                if event.node in _PANELS:
                    report = event.report
                    body = (
                        "\n".join(f"• {f}" for f in report.findings) or "(no findings)"
                    )
                    self.query_one(f"#{event.node}", Static).update(body)
```

with:

```python
            elif isinstance(event, NodeCompleteEvent):
                if event.node in _PANELS:
                    report = event.report
                    if report.failed:
                        self.query_one(f"#{event.node}", Static).update(
                            "[red]failed — see Status / Errors below[/red]"
                        )
                    else:
                        body = (
                            "\n".join(f"• {f}" for f in report.findings)
                            or "(no findings)"
                        )
                        self.query_one(f"#{event.node}", Static).update(body)
```

- [ ] **Step 3h: Wrap the runner loop and route run/config/evidence errors to the log**

In `_run`, wrap the `async for event in self._runner(...)` loop in a try/except (keep the existing body indented inside `try`), adding after the loop's `except`:

```python
        try:
            async for event in self._runner(
                initiative,
                evidence,
                portfolio=portfolio,
                outcomes=outcomes,
                approver=self._ask_human,
            ):
                ...  # existing dispatch body, unchanged
        except Exception as exc:  # noqa: BLE001 - never crash the worker
            self._log_status(f"run failed: {exc}", level="error")
            return
```

In `on_input_submitted`, replace the runner-None branch:

```python
        if self._runner is None:
            reason = self._runner_error or "model not configured"
            self.query_one("#strategist", Static).update(
                f"Cannot run — {reason}\n\n"
                "Open the menu (ctrl+h) to fix your provider/key, or install the "
                "provider's integration package, then restart."
            )
            return
```

with:

```python
        if self._runner is None:
            reason = self._runner_error or "model not configured"
            self._log_status(
                f"Cannot run — {reason}. Open the menu (ctrl+h) to fix your "
                "provider/key, or install the provider's integration package.",
                level="error",
            )
            return
```

And replace the evidence-error branch:

```python
        except EvidenceError as exc:
            self.query_one("#strategist", Static).update(f"Evidence error: {exc}")
            return
```

with:

```python
        except EvidenceError as exc:
            self._log_status(f"Evidence error: {exc}", level="error")
            return
```

- [ ] **Step 3i: Reset status + failed state on each new run**

In `on_input_submitted`, in the reset block (where `#debate`, `#risk`, `#governance` are set to `…`), add after those updates:

```python
        self._status_lines = []
        self.query_one("#status-log", Static).update("")
        for widget_id, base in _TITLES.items():
            if widget_id == "status-log":
                continue
            try:
                widget = self.query_one(f"#{widget_id}")
            except NoMatches:
                continue
            widget.remove_class("failed")
            widget.styles.border = None
            widget.border_title = base
```

- [ ] **Step 3j: Add status-log + `.failed` styling to `app.tcss`**

Append to `src/productagents/tui/app.tcss`:

```css
#status-log {
    dock: bottom;
    height: 8;
    margin: 0 1 1 1;
    border: round $error;
    padding: 0 1;
    overflow-y: auto;
}

.failed {
    border: round $error;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tui.py -k "node_error or bad_evidence or runner_unavailable"`
Expected: PASS. Then run the full TUI file: `uv run pytest tests/test_tui.py` — all green.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/tui/app.py src/productagents/tui/app.tcss tests/test_tui.py
git commit -m "feat: add Status/Errors panel and failed-panel badges to the TUI"
```

---

### Task 4: Three-lane layout with analyst grid

**Files:**
- Modify: `src/productagents/tui/app.py` (`compose()` only)
- Modify: `src/productagents/tui/app.tcss`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `_TITLES`, the status-log widget from Task 3.
- Produces: container ids `top-bar`, `lanes`, `left-lane`, `center-lane`, `right-lane`, `analyst-grid`. All existing panel ids (`customer_research`, `product_analytics`, `market`, `business`, `technical`, `debate`, `debate-scroll`, `recall`, `strategist`, `risk`, `risk-scroll`, `governance`, `evidence-provenance`, `status-log`, `initiative-title`, `evidence-source`) are preserved.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tui.py`:

```python
async def test_app_uses_three_lane_layout_with_analyst_grid():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        # New lane containers exist.
        app.query_one("#left-lane")
        app.query_one("#center-lane")
        app.query_one("#right-lane")
        grid = app.query_one("#analyst-grid")
        # All five analyst panels live inside the grid.
        for analyst_id in (
            "customer_research",
            "product_analytics",
            "market",
            "business",
            "technical",
        ):
            assert app.query_one(f"#{analyst_id}") in grid.query(".analyst")
        # Existing panels are still reachable by id.
        app.query_one("#debate")
        app.query_one("#risk")
        app.query_one("#governance")
        app.query_one("#strategist")
        app.query_one("#recall")
        app.query_one("#evidence-provenance")
        app.query_one("#status-log")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tui.py::test_app_uses_three_lane_layout_with_analyst_grid -x`
Expected: FAIL with `NoMatches` on `#left-lane`.

- [ ] **Step 3a: Update imports in `app.py`**

Change the containers import to include `Grid` and `Vertical`:

```python
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
```

- [ ] **Step 3b: Rewrite `compose()`**

Replace the entire `compose()` method body with:

```python
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-bar"):
            yield Input(
                placeholder="Describe the initiative and press Enter…",
                id="initiative-title",
            )
            yield Input(
                placeholder="Evidence source (scenario name or path; blank = sample)",
                id="evidence-source",
            )
        with Horizontal(id="lanes"):
            with VerticalScroll(id="left-lane"):
                yield Static("Waiting…", id="evidence-provenance", classes="panel")
                yield Static("Waiting…", id="recall", classes="panel")
            with Vertical(id="center-lane"):
                with Grid(id="analyst-grid"):
                    yield Static(
                        "Waiting…", id="customer_research", classes="panel analyst"
                    )
                    yield Static(
                        "Waiting…", id="product_analytics", classes="panel analyst"
                    )
                    yield Static("Waiting…", id="market", classes="panel analyst")
                    yield Static("Waiting…", id="business", classes="panel analyst")
                    yield Static("Waiting…", id="technical", classes="panel analyst")
                with VerticalScroll(id="debate-scroll"):
                    yield Static("Waiting…", id="debate")
            with Vertical(id="right-lane"):
                yield Static("Waiting…", id="strategist", classes="panel")
                with VerticalScroll(id="risk-scroll"):
                    yield Static("Waiting…", id="risk")
                yield Static("Waiting…", id="governance", classes="panel")
        yield Static("", id="status-log", classes="panel")
        yield Footer()
```

- [ ] **Step 3c: Replace the layout rules in `app.tcss`**

Replace the existing `#initiative-title`, `#analysts`, `#debate-scroll`, `#risk-scroll` rules at the top of `src/productagents/tui/app.tcss` with the lane layout. Specifically remove the old `#initiative-title { dock: top; … }` and `#analysts { height: auto; }` rules and add:

```css
#top-bar {
    dock: top;
    height: auto;
    margin: 1 1 0 1;
}

#initiative-title {
    width: 2fr;
}

#evidence-source {
    width: 3fr;
    margin-left: 1;
}

#lanes {
    height: 1fr;
}

#left-lane {
    width: 26%;
}

#center-lane {
    width: 1fr;
}

#right-lane {
    width: 32%;
}

#analyst-grid {
    grid-size: 3 2;
    grid-gutter: 1;
    height: 2fr;
}

.analyst {
    height: 100%;
    overflow-y: auto;
}

#debate-scroll {
    height: 1fr;
    margin: 1;
    border: round $accent;
}

#risk-scroll {
    height: 1fr;
    margin: 1;
    border: round $warning;
}
```

(Leave the existing `#debate`, `#risk`, `.panel`, `#strategist`, `#governance` rules in place — `.panel` still supplies the rounded border/padding for the lane panels.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tui.py::test_app_uses_three_lane_layout_with_analyst_grid -x`
Expected: PASS. Then `uv run pytest tests/test_tui.py` — full file green (existing content/render assertions still hold since all ids are preserved).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/tui/app.py src/productagents/tui/app.tcss tests/test_tui.py
git commit -m "feat: reorganize TUI into three lanes with an analyst grid"
```

---

### Task 5: Cohesive theme, per-stage accents, and status icons

**Files:**
- Modify: `src/productagents/tui/app.py`
- Modify: `src/productagents/tui/app.tcss`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `_TITLES`, `_PANELS`, `_WIDGET_FOR_NODE`, and the event dispatch from Tasks 3–4.
- Produces: module dict `_STATE_ICON` and method `_set_state(self, widget_id: str, state: str) -> None` where `state` ∈ `{"idle", "running", "done", "failed"}`; a registered Textual theme named `"productagents"` applied on mount.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tui.py`:

```python
async def test_app_registers_and_applies_custom_theme():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.theme == "productagents"


async def test_app_panel_titles_show_state_icons():
    from productagents.runner import FinishedEvent, NodeCompleteEvent
    from productagents.schemas import AnalystReport, Evidence, Recommendation

    async def fake_runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        yield NodeCompleteEvent(
            node="market",
            report=AnalystReport(
                analyst="market", role="Market Analyst", findings=["x"], signals=[]
            ),
        )
        yield FinishedEvent(
            recommendation=Recommendation(
                recommendation="Build it",
                confidence=0.5,
                rationale="r",
                expected_outcomes=["o"],
            ),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
        )

    evidence = Evidence(
        scenario="sample", customer_feedback="d", product_analytics={"x": 1}
    )
    app = ProductAgentsApp(
        fake_runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        # Idle on mount.
        assert str(app.query_one("#technical").border_title).startswith("·")
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        # Completed analyst shows the done icon.
        assert "✓" in str(app.query_one("#market").border_title)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tui.py -k "custom_theme or state_icons" -x`
Expected: FAIL — no `productagents` theme; titles have no icons.

- [ ] **Step 3a: Define and register the theme**

In `src/productagents/tui/app.py`, add the import:

```python
from textual.theme import Theme
```

Add at module level (after `_WIDGET_FOR_NODE`):

```python
_THEME = Theme(
    name="productagents",
    primary="#38bdf8",
    secondary="#a78bfa",
    accent="#f59e0b",
    success="#22c55e",
    warning="#fb923c",
    error="#ef4444",
    surface="#1e293b",
    panel="#0f172a",
    dark=True,
)

_STATE_ICON = {"idle": "·", "running": "●", "done": "✓", "failed": "✗"}
```

In `on_mount`, register and apply the theme **before** setting titles:

```python
    def on_mount(self) -> None:
        self.register_theme(_THEME)
        self.theme = "productagents"
        for widget_id in _TITLES:
            if widget_id == "status-log":
                self.query_one("#status-log").border_title = _TITLES[widget_id]
            else:
                self._set_state(widget_id, "idle")
        if self._show_home:
            self._open_home()
```

- [ ] **Step 3b: Add `_set_state` and route it through the lifecycle**

Add the method to `ProductAgentsApp`:

```python
    def _set_state(self, widget_id: str, state: str) -> None:
        try:
            widget = self.query_one(f"#{widget_id}")
        except NoMatches:
            return
        base = _TITLES.get(widget_id, widget_id)
        widget.border_title = f"{_STATE_ICON[state]} {base}"
```

Update `_mark_failed` to reuse it — replace its `if base:` tail:

```python
        if base:
            panel.border_title = f"✗ {base}"
```

with:

```python
        self._set_state(widget_id, "failed")
```

In the `_run` dispatch, set running/done states:
- In the `ProgressEvent` branch, after updating the panel text, add:

```python
            if isinstance(event, ProgressEvent):
                if event.node in _PANELS:
                    self.query_one(f"#{event.node}", Static).update(
                        f"… {event.message}"
                    )
                    self._set_state(event.node, "running")
```

- In the `NodeCompleteEvent` branch, after updating text (both the failed and success paths), set done for the success path. Add `self._set_state(event.node, "done")` inside the `else:` (non-failed) sub-branch added in Task 3.
- In the `RecallEvent` branch, after updating `#recall`, add `self._set_state("recall", "done")`.
- In the `FinishedEvent` branch, after `self._render_recommendation(recommendation)`, add `self._set_state("strategist", "done")`.

- [ ] **Step 3c: Reset to idle on a new run**

In `on_input_submitted`'s reset block from Task 3, replace `widget.border_title = base` with a state reset. Change:

```python
            widget.remove_class("failed")
            widget.styles.border = None
            widget.border_title = base
```

to:

```python
            widget.remove_class("failed")
            widget.styles.border = None
            self._set_state(widget_id, "idle")
```

(The `status-log` entry is already skipped by the `continue` above it.)

- [ ] **Step 3d: Add per-stage accent borders to `app.tcss`**

Append to `src/productagents/tui/app.tcss`:

```css
/* Per-stage accent borders (failed state overrides via inline style). */
.analyst {
    border: round #38bdf8;   /* analysts — cyan */
}

#debate-scroll {
    border: round #f59e0b;   /* debate — amber */
}

#strategist {
    border: round #22c55e;   /* strategy — green */
}

#risk-scroll {
    border: round #fb923c;   /* risk — orange */
}

#governance {
    border: round #a78bfa;   /* governance — violet */
}

#recall, #evidence-provenance {
    border: round $primary;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tui.py -k "custom_theme or state_icons"`
Expected: PASS. Then the full TUI file: `uv run pytest tests/test_tui.py`.

> Note: a couple of existing tests assert exact text in panels (e.g. `"approve" in gov_text`). Those still pass — `_set_state` only changes `border_title`, not panel `content`. The state-icon test (`test_app_panel_titles_show_state_icons`) is the one that locks the icon behavior.

- [ ] **Step 5: Run the full suite + coverage gate, then refresh the graph**

```bash
uv run pytest
graphify update .
```

Expected: all tests pass; coverage ≥ 90%.

- [ ] **Step 6: Commit**

```bash
git add src/productagents/tui/app.py src/productagents/tui/app.tcss tests/test_tui.py
git commit -m "feat: themed TUI with per-stage accents and panel state icons"
```

---

## Self-Review

**Spec coverage:**
- "organize using not only horizontal lanes but also vertical ones" → **Task 4** (3-column `Horizontal` of vertical lanes + a 3×2 analyst `Grid` mixing both axes).
- "make the UI look better" → **Task 5** (custom theme, per-stage accent colors, `·/●/✓/✗` state icons) + Task 4's grid de-cluttering.
- "new section for error throwing … reached API KEY rate limit, but nothing changed" → **Tasks 1–3**: the rate-limit `Exception` inside `run_analyst` now emits an `error` chunk → `NodeErrorEvent` → a docked **Status / Errors** panel logs `technical: 429 …` and the panel gets a red `✗ FAILED` badge. Root cause (the `(no findings)` overwrite) is fixed in Task 3 Step 3g.

**Placeholder scan:** The only `...` is in Task 3 Step 3h, where it explicitly stands for "existing dispatch body, unchanged" (a wrap-in-try instruction, not new code to invent). All other steps contain complete code.

**Type consistency:** `NodeErrorEvent(node, message)` is defined once (Task 1) and consumed with those exact field names in Task 3. `_TITLES`/`_WIDGET_FOR_NODE`/`_set_state`/`_STATE_ICON` names are consistent across Tasks 3 and 5. Widget ids in `compose()` (Task 4) match every `query_one`/`_TITLES` key. `_set_state` states (`idle`/`running`/`done`/`failed`) match `_STATE_ICON` keys.

**Note for the executor:** Run `uv run productagents` once after Task 5 to eyeball the layout in a real terminal — automated tests assert structure and behavior, not visual proportions. Tweak the lane `width:` percentages and `grid-size` heights to taste; they don't affect tests.
