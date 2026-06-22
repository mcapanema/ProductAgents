# TUI Per-Section State Indicators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every TUI panel a clear live status in its border title — an animated "spinning circle" while running, a "waiting on upstream" sign before a node's turn, a warning sign for soft-fail verdicts, and the existing error sign for hard failures.

**Architecture:** The TUI already drives a tiny per-panel state machine: `_set_state(widget_id, state)` writes `f"{icon} {title}"` into a widget's `border_title`, with icons looked up from the module-level `_STATE_ICON` dict (`src/productagents/tui/app.py`). We extend that state machine with two new states (`waiting`, `warning`) and replace the static `running` glyph with a timer-driven animated spinner. No runner/graph/schema changes are needed — every signal we react to is already an event the TUI handles. We also add cross-panel handoff transitions so scroll panels (debate, risk) and the strategist flip from running→done at the right moments.

**Tech Stack:** Python ≥ 3.14, Textual (App, `set_interval` timers, `border_title`, CSS classes), `app.tcss` stylesheet, pytest with Textual's `run_test()` pilot (offline, no API key).

## Global Constraints

- Python ≥ 3.14, managed with **uv** (not Conda/pip). Run everything via `uv run`.
- Tests run **fully offline** — no API key, no network. Use Textual's `run_test()` pilot and the injected fakes (`tests/fakes.py::FakeChatModel`).
- Coverage gate is enforced: `--cov-fail-under=90` (configured in `pyproject.toml`, runs automatically under `uv run pytest`). Every new branch needs a test.
- `asyncio_mode = "auto"` — write `async def test_*` with **no** decorator.
- **Nodes degrade, never crash** is a package-wide rule, but this plan touches only the TUI layer (`tui/app.py`, `tui/app.tcss`) and its tests (`tests/test_tui.py`). Do not modify `runner.py`, `graph.py`, `schemas.py`, or any `agents/` node.
- After editing code, the project convention is to run `graphify update .` (AST-only, no API cost) — do this once at the end, not per task.
- Keep glyphs single-width and monochrome to avoid terminal alignment issues: waiting `◌` (U+25CC), warning `⚠` (U+26A0), done `✓`, failed `✗`, spinner frames `◐◓◑◒` (U+25D0–25D3).

---

## File Structure

| File | Change | Responsibility |
| --- | --- | --- |
| `src/productagents/tui/app.py` | Modify | Owns the panel state machine. Add `waiting`/`warning` icons, the spinner constants + timer machinery, the `_WAITING_AT_START` set, and the cross-panel handoff transitions in event handlers. |
| `src/productagents/tui/app.tcss` | Modify | Add a `.warning` border-color class mirroring the existing `.failed`. |
| `tests/test_tui.py` | Modify | Add headless pilot tests for: downstream panels start `waiting`; running shows an advancing spinner that stops on completion; judge-fail and governance non-approve show `warning` (+ class), approve clears it; debate/risk scroll panels and the strategist transition running→done. |

### Reference: current relevant code in `src/productagents/tui/app.py`

```python
# line 91
_STATE_ICON = {"idle": "·", "running": "●", "done": "✓", "failed": "✗"}

# lines 185-191
def _set_state(self, widget_id: str, state: str) -> None:
    try:
        widget = self.query_one(f"#{widget_id}")
    except NoMatches:
        return
    base = _TITLES.get(widget_id, widget_id)
    widget.border_title = f"{_STATE_ICON[state]} {base}"
```

`_TITLES` (lines 45-59) maps every widget id — including `"debate-scroll"`, `"risk-scroll"`, `"strategist"`, `"judgment"`, `"governance"`, and the five analysts — to a human title, so `_set_state` works for all of them. `_WIDGET_FOR_NODE` (lines 62-65) maps the runner node names `"debate"→"debate-scroll"` and `"risk"→"risk-scroll"`. `_PANELS` (lines 68-76) is the set of node ids with a dedicated analyst/recall/strategist panel.

---

### Task 1: Add the `waiting` state and start downstream panels waiting on run

**Files:**
- Modify: `src/productagents/tui/app.py:91` (`_STATE_ICON`), add a `_WAITING_AT_START` constant, rewrite `_reset_panels` (lines 250-270)
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: existing `_set_state(widget_id: str, state: str)`, `_TITLES`, `ProductAgentsApp._reset_panels()`.
- Produces: `_STATE_ICON` gains a `"waiting": "◌"` key; new module constant `_WAITING_AT_START: set[str]`; `_reset_panels()` now sets the five downstream panels (`debate-scroll`, `strategist`, `judgment`, `risk-scroll`, `governance`) to `"waiting"` and all other panels to `"idle"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tui.py` (after the existing `test_app_uses_three_lane_layout_with_analyst_grid` test or anywhere at module scope):

```python
async def test_reset_panels_marks_downstream_waiting():
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
        app._reset_panels()
        # Downstream panels wait on upstream output.
        for widget_id in ("debate-scroll", "strategist", "judgment", "risk-scroll",
                          "governance"):
            assert str(app.query_one(f"#{widget_id}").border_title).startswith("◌")
        # Analysts and recall do not wait — they start immediately.
        assert str(app.query_one("#technical").border_title).startswith("·")
        assert str(app.query_one("#recall").border_title).startswith("·")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tui.py::test_reset_panels_marks_downstream_waiting -x`
Expected: FAIL — currently `_reset_panels` sets every panel to `"idle"` (`·`), so the downstream `◌` assertions fail (and `_STATE_ICON` has no `"waiting"` key, which would raise `KeyError` once `_reset_panels` is changed — that is the next step).

- [ ] **Step 3: Add the `waiting` icon and the `_WAITING_AT_START` constant**

In `src/productagents/tui/app.py`, replace line 91:

```python
_STATE_ICON = {"idle": "·", "running": "●", "done": "✓", "failed": "✗"}
```

with:

```python
_STATE_ICON = {
    "idle": "·",
    "waiting": "◌",
    "running": "●",
    "done": "✓",
    "failed": "✗",
    "warning": "⚠",
}

# Spinner frames for the "running" state (a rotating filled circle).
_SPINNER_FRAMES = "◐◓◑◒"

# Downstream panels that depend on upstream output; they show "waiting" at the
# start of a run until their first event flips them to running.
_WAITING_AT_START = {
    "debate-scroll",
    "strategist",
    "judgment",
    "risk-scroll",
    "governance",
}
```

(`_SPINNER_FRAMES` and the `"warning"`/`"running"` icons are added now so later tasks only touch behavior; they are unused until Tasks 2–3.)

- [ ] **Step 4: Rewrite `_reset_panels` to seed waiting vs idle**

In `src/productagents/tui/app.py`, replace the current `_reset_panels` (lines 250-270):

```python
    def _reset_panels(self) -> None:
        """Clear every live panel back to its pre-run placeholder."""
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._debate_lines = []
        self._risk_lines = []
        self.query_one("#debate", Static).update("…")
        self.query_one("#risk", Static).update("…")
        self.query_one("#governance", Static).update("…")
        self.query_one("#judgment", Static).update("…")
        self._status_lines = []
        self.query_one("#status-log", Static).update("")
        for widget_id in _TITLES:
            if widget_id == "status-log":
                continue
            try:
                widget = self.query_one(f"#{widget_id}")
            except NoMatches:
                continue
            widget.remove_class("failed")
            self._set_state(widget_id, "idle")
```

with:

```python
    def _reset_panels(self) -> None:
        """Clear every live panel back to its pre-run placeholder."""
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._debate_lines = []
        self._risk_lines = []
        self.query_one("#debate", Static).update("…")
        self.query_one("#risk", Static).update("…")
        self.query_one("#governance", Static).update("…")
        self.query_one("#judgment", Static).update("…")
        self._status_lines = []
        self.query_one("#status-log", Static).update("")
        for widget_id in _TITLES:
            if widget_id == "status-log":
                continue
            state = "waiting" if widget_id in _WAITING_AT_START else "idle"
            self._set_state(widget_id, state)
```

Note: the per-widget `try/except NoMatches` and `remove_class("failed")` are dropped here because `_set_state` already swallows `NoMatches` (lines 186-189) and Task 3 will move class management into `_set_state`. For now `_set_state` does not touch the `failed` class, but `_reset_panels` setting a panel to `idle`/`waiting` after a previous run's failure is acceptable: a fresh run always re-emits events, and Task 3 makes the class clearing explicit. If you are implementing Task 1 in isolation and want to preserve exact behavior, leave the `widget.remove_class("failed")` by querying inside the loop — but the canonical end state after Task 3 is the version above.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_tui.py::test_reset_panels_marks_downstream_waiting -x`
Expected: PASS

- [ ] **Step 6: Run the full TUI test file to confirm no regressions**

Run: `uv run pytest tests/test_tui.py`
Expected: PASS (the existing idle/done icon assertions at the old lines 593/599 still hold — `·` and `✓` are unchanged).

- [ ] **Step 7: Commit**

```bash
git add src/productagents/tui/app.py tests/test_tui.py
git commit -m "feat(tui): add waiting state for downstream panels at run start

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LAoJatEiP8ybCPzGf49xTW"
```

---

### Task 2: Replace the static running glyph with an animated spinner

**Files:**
- Modify: `src/productagents/tui/app.py` — `__init__` (add spinner state, lines 133-135 area), `_set_state` (lines 185-191), add `_paint_state` / `_ensure_spinner` / `_advance_spinner`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `_SPINNER_FRAMES` (added in Task 1), `_STATE_ICON`, `_TITLES`, Textual `App.set_interval`.
- Produces:
  - New instance attributes `self._spinning: set[str]`, `self._spinner_frame: int`, `self._spinner_timer` (Textual `Timer | None`).
  - `_set_state(widget_id, "running")` now registers the widget in `self._spinning`, starts the timer, and paints the current frame; any other state discards it and paints the static icon.
  - New methods `_paint_state(self, widget_id: str, icon: str) -> None`, `_ensure_spinner(self) -> None`, `_advance_spinner(self) -> None`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tui.py`:

```python
async def test_running_state_shows_advancing_spinner_that_stops_on_done():
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
        app._set_state("market", "running")
        title_before = str(app.query_one("#market").border_title)
        assert title_before[0] in "◐◓◑◒"
        assert "market" in app._spinning
        # Advancing the timer rotates the frame.
        app._advance_spinner()
        title_after = str(app.query_one("#market").border_title)
        assert title_after[0] in "◐◓◑◒"
        assert title_after != title_before
        # Reaching a terminal state stops the spin and paints the static icon.
        app._set_state("market", "done")
        assert "market" not in app._spinning
        assert str(app.query_one("#market").border_title).startswith("✓")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tui.py::test_running_state_shows_advancing_spinner_that_stops_on_done -x`
Expected: FAIL with `AttributeError: 'ProductAgentsApp' object has no attribute '_spinning'` (and no `_advance_spinner`).

- [ ] **Step 3: Add the spinner instance state to `__init__`**

In `src/productagents/tui/app.py`, find the end of `__init__` (lines 133-135):

```python
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []
        self._status_lines: list[str] = []
```

and append the spinner state:

```python
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []
        self._status_lines: list[str] = []
        self._spinning: set[str] = set()
        self._spinner_frame: int = 0
        self._spinner_timer = None
```

- [ ] **Step 4: Rewrite `_set_state` and add the spinner helpers**

In `src/productagents/tui/app.py`, replace `_set_state` (lines 185-191):

```python
    def _set_state(self, widget_id: str, state: str) -> None:
        try:
            widget = self.query_one(f"#{widget_id}")
        except NoMatches:
            return
        base = _TITLES.get(widget_id, widget_id)
        widget.border_title = f"{_STATE_ICON[state]} {base}"
```

with:

```python
    def _set_state(self, widget_id: str, state: str) -> None:
        if state == "running":
            self._spinning.add(widget_id)
            self._ensure_spinner()
            self._paint_state(widget_id, _SPINNER_FRAMES[self._spinner_frame])
        else:
            self._spinning.discard(widget_id)
            self._paint_state(widget_id, _STATE_ICON[state])

    def _paint_state(self, widget_id: str, icon: str) -> None:
        try:
            widget = self.query_one(f"#{widget_id}")
        except NoMatches:
            return
        base = _TITLES.get(widget_id, widget_id)
        widget.border_title = f"{icon} {base}"

    def _ensure_spinner(self) -> None:
        if self._spinner_timer is None:
            self._spinner_timer = self.set_interval(0.12, self._advance_spinner)

    def _advance_spinner(self) -> None:
        if not self._spinning:
            return
        self._spinner_frame = (self._spinner_frame + 1) % len(_SPINNER_FRAMES)
        frame = _SPINNER_FRAMES[self._spinner_frame]
        for widget_id in self._spinning:
            self._paint_state(widget_id, frame)
```

Note: `set_interval` is a Textual `App` method available after mount; `running` is only ever set during an active (mounted) run, so the timer is created lazily and safely. The timer runs for the app's lifetime; `_advance_spinner` is a no-op when nothing is spinning.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_tui.py::test_running_state_shows_advancing_spinner_that_stops_on_done -x`
Expected: PASS

- [ ] **Step 6: Run the full TUI test file**

Run: `uv run pytest tests/test_tui.py`
Expected: PASS. The existing run at old line 599 asserts `✓` appears in `#market` after completion — still true. No test asserts the old `●` running glyph, so nothing breaks.

- [ ] **Step 7: Commit**

```bash
git add src/productagents/tui/app.py tests/test_tui.py
git commit -m "feat(tui): animate the running state with a spinning circle

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LAoJatEiP8ybCPzGf49xTW"
```

---

### Task 3: Add the `warning` state for soft-fail verdicts (judge fail, governance non-approve)

**Files:**
- Modify: `src/productagents/tui/app.py` — `_set_state` (class management), `_on_judgment` (line 381), `_on_governance_verdict` (lines 383-386), `_on_final_verdict` (lines 388-391), `_mark_failed` (lines 422-429)
- Modify: `src/productagents/tui/app.tcss` — add `.warning` rule after `.failed` (line 154)
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `_set_state`, `_STATE_ICON["warning"] == "⚠"` (added in Task 1), `JudgmentEvent`, `GovernanceVerdictEvent`, `FinalVerdictEvent` from `productagents.runner`.
- Produces:
  - `_set_state` now centrally manages the `failed`/`warning` CSS classes: it removes both, then adds the one matching the state.
  - `_on_judgment` paints `judgment` as `done` (pass) or `warning` (fail) — previously `failed`.
  - `_on_governance_verdict` / `_on_final_verdict` paint `governance` as `done` when `verdict == "approve"`, else `warning`.
  - `_mark_failed` is simplified to delegate class handling to `_set_state`.

- [ ] **Step 1: Add the runner-event imports the tests need**

In `tests/test_tui.py`, the `from productagents.runner import run_decision` line (line 6) imports only `run_decision`. Replace it with:

```python
from productagents.runner import (
    FinalVerdictEvent,
    GovernanceVerdictEvent,
    JudgmentEvent,
    run_decision,
)
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_tui.py`:

```python
async def test_judgment_failure_shows_warning():
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
        app._on_judgment(
            JudgmentEvent(
                evidence_grounding_score=0.4,
                rationale_coherence_score=0.5,
                passed=False,
                critique="weak grounding",
                attempt=1,
            )
        )
        panel = app.query_one("#judgment")
        assert str(panel.border_title).startswith("⚠")
        assert panel.has_class("warning")


async def test_governance_non_approve_warns_then_approval_clears_it():
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
        app._on_governance_verdict(
            GovernanceVerdictEvent(verdict="reject", rationale="not now")
        )
        gov = app.query_one("#governance")
        assert str(gov.border_title).startswith("⚠")
        assert gov.has_class("warning")
        # A human override to approve clears the warning.
        app._on_final_verdict(
            FinalVerdictEvent(verdict="approve", rationale="ok", decided_by="human")
        )
        assert str(gov.border_title).startswith("✓")
        assert not gov.has_class("warning")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_tui.py::test_judgment_failure_shows_warning tests/test_tui.py::test_governance_non_approve_warns_then_approval_clears_it -x`
Expected: FAIL — `_on_judgment` currently sets `failed` (`✗`, no `warning` class); governance handlers don't set any state.

- [ ] **Step 4: Centralize class management in `_set_state`**

In `src/productagents/tui/app.py`, update `_set_state` (the version from Task 2) to clear and re-apply the `failed`/`warning` classes. Replace:

```python
    def _set_state(self, widget_id: str, state: str) -> None:
        if state == "running":
            self._spinning.add(widget_id)
            self._ensure_spinner()
            self._paint_state(widget_id, _SPINNER_FRAMES[self._spinner_frame])
        else:
            self._spinning.discard(widget_id)
            self._paint_state(widget_id, _STATE_ICON[state])
```

with:

```python
    def _set_state(self, widget_id: str, state: str) -> None:
        try:
            widget = self.query_one(f"#{widget_id}")
        except NoMatches:
            return
        widget.remove_class("failed", "warning")
        if state == "failed":
            widget.add_class("failed")
        elif state == "warning":
            widget.add_class("warning")
        if state == "running":
            self._spinning.add(widget_id)
            self._ensure_spinner()
            self._paint_state(widget_id, _SPINNER_FRAMES[self._spinner_frame])
        else:
            self._spinning.discard(widget_id)
            self._paint_state(widget_id, _STATE_ICON[state])
```

- [ ] **Step 5: Use `warning` in the judgment and governance handlers**

In `src/productagents/tui/app.py`, replace the last line of `_on_judgment` (line 381):

```python
        self._set_state("judgment", "done" if event.passed else "failed")
```

with:

```python
        self._set_state("judgment", "done" if event.passed else "warning")
```

Replace `_on_governance_verdict` (lines 383-386):

```python
    def _on_governance_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            f"[b]{event.verdict}[/b]\n\n{event.rationale}"
        )
```

with:

```python
    def _on_governance_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            f"[b]{event.verdict}[/b]\n\n{event.rationale}"
        )
        state = "done" if event.verdict == "approve" else "warning"
        self._set_state("governance", state)
```

Replace `_on_final_verdict` (lines 388-391):

```python
    def _on_final_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            f"[b]FINAL ({event.decided_by}): {event.verdict}[/b]\n\n{event.rationale}"
        )
```

with:

```python
    def _on_final_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            f"[b]FINAL ({event.decided_by}): {event.verdict}[/b]\n\n{event.rationale}"
        )
        state = "done" if event.verdict == "approve" else "warning"
        self._set_state("governance", state)
```

- [ ] **Step 6: Simplify `_mark_failed` to delegate class handling**

In `src/productagents/tui/app.py`, replace `_mark_failed` (lines 422-429):

```python
    def _mark_failed(self, node: str) -> None:
        widget_id = _WIDGET_FOR_NODE.get(node, node)
        try:
            panel = self.query_one(f"#{widget_id}")
        except NoMatches:
            return
        panel.add_class("failed")
        self._set_state(widget_id, "failed")
```

with:

```python
    def _mark_failed(self, node: str) -> None:
        widget_id = _WIDGET_FOR_NODE.get(node, node)
        self._set_state(widget_id, "failed")
```

(`_set_state("failed")` now adds the `failed` class and swallows `NoMatches`.)

- [ ] **Step 7: Add the `.warning` CSS rule**

In `src/productagents/tui/app.tcss`, find the `.failed` rule (lines 154-156):

```css
.failed {
    border: round $error;
}
```

and add the `.warning` rule directly after it:

```css
.failed {
    border: round $error;
}

.warning {
    border: round $warning;
}
```

- [ ] **Step 8: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_tui.py::test_judgment_failure_shows_warning tests/test_tui.py::test_governance_non_approve_warns_then_approval_clears_it -x`
Expected: PASS

- [ ] **Step 9: Run the full TUI test file**

Run: `uv run pytest tests/test_tui.py`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add src/productagents/tui/app.py src/productagents/tui/app.tcss tests/test_tui.py
git commit -m "feat(tui): warn on judge-fail and non-approve governance verdicts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LAoJatEiP8ybCPzGf49xTW"
```

---

### Task 4: Drive debate/risk scroll panels and the strategist through running→done

**Files:**
- Modify: `src/productagents/tui/app.py` — `_on_progress` (lines 339-342), `_on_debate_turn` (lines 363-367), `_on_risk_assessment` (lines 369-371), `_on_judgment` (add strategist-done), `_on_governance_verdict` (add risk-done)
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `_set_state`, the runner events `ProgressEvent`, `DebateTurnEvent`, `RiskAssessmentEvent`, `JudgmentEvent`, `GovernanceVerdictEvent`.
- Produces panel-state transitions:
  - First `DebateTurnEvent` → `debate-scroll` = running.
  - `ProgressEvent(node="strategist")` → `debate-scroll` = done (debate finished), then `strategist` = running (spinner).
  - `JudgmentEvent` → `strategist` = done (strategist finished before the judge ran), then `judgment` = done/warning (from Task 3).
  - First `RiskAssessmentEvent` → `risk-scroll` = running.
  - `GovernanceVerdictEvent` → `risk-scroll` = done (risk finished before governance), then `governance` = done/warning (from Task 3).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tui.py`. Add `DebateTurnEvent`, `ProgressEvent`, `RiskAssessmentEvent` to the runner import block edited in Task 3 so it reads:

```python
from productagents.runner import (
    DebateTurnEvent,
    FinalVerdictEvent,
    GovernanceVerdictEvent,
    JudgmentEvent,
    ProgressEvent,
    RiskAssessmentEvent,
    run_decision,
)
```

Then add the tests:

```python
async def test_debate_panel_runs_then_done_when_strategist_starts():
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
        app._on_debate_turn(
            DebateTurnEvent(round=1, side="advocate", argument="ship it")
        )
        assert "debate-scroll" in app._spinning  # running spinner
        app._on_progress(ProgressEvent(node="strategist", message="thinking"))
        assert str(app.query_one("#debate-scroll").border_title).startswith("✓")
        assert "strategist" in app._spinning


async def test_strategist_done_when_judgment_arrives():
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
        app._on_progress(ProgressEvent(node="strategist", message="thinking"))
        assert "strategist" in app._spinning
        app._on_judgment(
            JudgmentEvent(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                passed=True,
                critique="ok",
                attempt=1,
            )
        )
        assert str(app.query_one("#strategist").border_title).startswith("✓")
        assert "strategist" not in app._spinning


async def test_risk_panel_runs_then_done_when_governance_arrives():
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
        app._on_risk_assessment(
            RiskAssessmentEvent(
                reviewer="r", role="Risk Reviewer", level="medium", rationale="some"
            )
        )
        assert "risk-scroll" in app._spinning
        app._on_governance_verdict(
            GovernanceVerdictEvent(verdict="approve", rationale="go")
        )
        assert str(app.query_one("#risk-scroll").border_title).startswith("✓")
        assert "risk-scroll" not in app._spinning
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_tui.py -k "debate_panel_runs or strategist_done_when_judgment or risk_panel_runs" -x`
Expected: FAIL — the handlers don't yet set `debate-scroll`/`risk-scroll` running, don't mark them done, and don't mark the strategist done on judgment.

- [ ] **Step 3: Mark debate-scroll running on each debate turn**

In `src/productagents/tui/app.py`, replace `_on_debate_turn` (lines 363-367):

```python
    def _on_debate_turn(self, event) -> None:
        self._debate_lines.append(
            f"[{event.side} · round {event.round}] {event.argument}"
        )
        self.query_one("#debate", Static).update("\n\n".join(self._debate_lines))
```

with:

```python
    def _on_debate_turn(self, event) -> None:
        self._debate_lines.append(
            f"[{event.side} · round {event.round}] {event.argument}"
        )
        self.query_one("#debate", Static).update("\n\n".join(self._debate_lines))
        self._set_state("debate-scroll", "running")
```

- [ ] **Step 4: Mark risk-scroll running on each risk assessment**

In `src/productagents/tui/app.py`, replace `_on_risk_assessment` (lines 369-371):

```python
    def _on_risk_assessment(self, event) -> None:
        self._risk_lines.append(f"[{event.role} · {event.level}] {event.rationale}")
        self.query_one("#risk", Static).update("\n\n".join(self._risk_lines))
```

with:

```python
    def _on_risk_assessment(self, event) -> None:
        self._risk_lines.append(f"[{event.role} · {event.level}] {event.rationale}")
        self.query_one("#risk", Static).update("\n\n".join(self._risk_lines))
        self._set_state("risk-scroll", "running")
```

- [ ] **Step 5: Finish debate when the strategist starts**

In `src/productagents/tui/app.py`, replace `_on_progress` (lines 339-342):

```python
    def _on_progress(self, event) -> None:
        if event.node in _PANELS:
            self.query_one(f"#{event.node}", Static).update(f"… {event.message}")
            self._set_state(event.node, "running")
```

with:

```python
    def _on_progress(self, event) -> None:
        if event.node in _PANELS:
            self.query_one(f"#{event.node}", Static).update(f"… {event.message}")
            if event.node == "strategist":
                self._set_state("debate-scroll", "done")
            self._set_state(event.node, "running")
```

- [ ] **Step 6: Finish the strategist when the judgment arrives, and risk when governance arrives**

In `src/productagents/tui/app.py`, in `_on_judgment` (post-Task-3 version), add a strategist-done line before the judgment state. Replace:

```python
        self._set_state("judgment", "done" if event.passed else "warning")
```

with:

```python
        self._set_state("strategist", "done")
        self._set_state("judgment", "done" if event.passed else "warning")
```

In `_on_governance_verdict` (post-Task-3 version), add a risk-done line. Replace:

```python
        state = "done" if event.verdict == "approve" else "warning"
        self._set_state("governance", state)
```

with:

```python
        self._set_state("risk-scroll", "done")
        state = "done" if event.verdict == "approve" else "warning"
        self._set_state("governance", state)
```

(Note: `_on_governance_verdict` appears once; this is the only occurrence of that two-line `state = ...` block, so the replacement is unambiguous.)

- [ ] **Step 7: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_tui.py -k "debate_panel_runs or strategist_done_when_judgment or risk_panel_runs" -x`
Expected: PASS

- [ ] **Step 8: Run the full suite with coverage**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90% (the new branches are covered by Tasks 1–4 tests).

- [ ] **Step 9: Refresh the knowledge graph**

Run: `graphify update .`
Expected: completes with no error (AST-only, no API cost).

- [ ] **Step 10: Commit**

```bash
git add src/productagents/tui/app.py tests/test_tui.py graphify-out
git commit -m "feat(tui): hand off debate/risk/strategist panels through running to done

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LAoJatEiP8ybCPzGf49xTW"
```

---

## Self-Review

**1. Spec coverage** (the four requested signals):
- *Spinning circle* → Task 2 (animated `◐◓◑◒` via `set_interval`, registered per running panel).
- *Warning sign* → Task 3 (`⚠` + `.warning` border for judge-fail and non-approve governance).
- *Error icon* → already present (`✗` + `.failed`); preserved and centralized into `_set_state` (Task 3). `NodeErrorEvent` still routes through `_mark_failed`.
- *"Waiting for another agent/step" sign* → Task 1 (`◌` on downstream panels at run start) + Task 4 (panels leave waiting→running→done as their events arrive, so the sign genuinely means "blocked on upstream").

**2. Placeholder scan:** Every code step shows the full before/after blocks. No "TBD"/"handle edge cases"/"similar to Task N". The one judgment-call note (Task 1 Step 4 about `remove_class`) is resolved deterministically by Task 3.

**3. Type/name consistency:**
- `_STATE_ICON` keys used: `idle`, `waiting`, `running`, `done`, `failed`, `warning` — all defined in Task 1. (`running` is in the dict for completeness but `_set_state` never indexes it after Task 2, since the running branch paints a spinner frame instead.)
- `_WAITING_AT_START`, `_SPINNER_FRAMES` defined in Task 1, consumed in Tasks 1/2.
- New methods `_paint_state`, `_ensure_spinner`, `_advance_spinner` defined and called consistently (Task 2).
- Instance attrs `_spinning`, `_spinner_frame`, `_spinner_timer` defined in `__init__` (Task 2) and used in `_set_state`/`_advance_spinner`/`_ensure_spinner`.
- Widget ids match `_TITLES`/the `compose` tree: `debate-scroll`, `risk-scroll`, `strategist`, `judgment`, `governance`, `recall`, `technical`, `market`.
- Runner event field names used in tests match `runner.py`: `JudgmentEvent(evidence_grounding_score, rationale_coherence_score, passed, critique, attempt)`, `GovernanceVerdictEvent(verdict, rationale)`, `FinalVerdictEvent(verdict, rationale, decided_by)`, `DebateTurnEvent(round, side, argument)`, `RiskAssessmentEvent(reviewer, role, level, rationale)`, `ProgressEvent(node, message)`.

No gaps found.
