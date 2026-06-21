# ProductAgents Review-Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the two optional, non-blocking hardening follow-ups raised by the PR #10 final review: guard the TUI `NodeCompleteEvent` handler against non-panel node ids, and consolidate the analyst-node test imports to the top of the file.

**Architecture:** Two small, independent changes. (1) The TUI's `NodeCompleteEvent` branch resolves `query_one(f"#{event.node}")` with no membership check, while the sibling `ProgressEvent` branch already guards with `if event.node in _PANELS:`. Today only the five analyst nodes emit `NodeCompleteEvent` (only they write `reports`), so every id has a panel — but the asymmetry is a latent crash for any future `reports`-writing node without a panel. We add the same guard for symmetry. (2) PR #10 appended three analyst-node imports mid-file in `tests/test_analysts.py`, each suppressed with `# noqa: E402`; we move them into the top import block and drop the suppressions.

**Tech Stack:** Python 3.14, UV, Textual, pytest + pytest-asyncio, ruff.

## Global Constraints

- Python `>=3.14`; UV only. Run all commands with `uv run ...` from the repo root.
- This plan targets `main` as of PR #10 (merge commit `b0e8951`). Run it on a fresh branch from `main`.
- **Ordering caveat vs. the outcome-injection plan:** if you have already executed `docs/superpowers/plans/2026-06-20-productagents-outcome-injection.md`, then `FinishedEvent` has an extra required `prior_lessons` field. In that case only, add `prior_lessons=[]` to the `FinishedEvent(...)` constructed in Task 1's test. On unmodified post-#10 `main`, `FinishedEvent` has exactly five fields (`recommendation`, `reports`, `debate`, `risks`, `governance`) and no change is needed.
- The TUI app's `_PANELS` dict drives panel titles (`on_mount`), the per-run reset (`on_input_submitted`), and `ProgressEvent` routing. The guard added in Task 1 makes `NodeCompleteEvent` routing consistent with that same dict.
- All tests run fully offline (`FakeChatModel` / injected fake runners / `tmp_path`) — no network, no API key. `asyncio_mode = "auto"`, so `async def test_*` functions need no decorator.
- Behavior of existing panels is unchanged: a `NodeCompleteEvent` whose node IS in `_PANELS` must still render exactly as before.
- TDD: failing test first, watch it fail, implement minimally, watch it pass, commit.

---

### Task 1: Guard the `NodeCompleteEvent` handler against non-panel nodes

**Files:**
- Modify: `src/productagents/tui/app.py`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `ProductAgentsApp(runner, evidence, *, recorder=..., reader=...)`; the runner is any async iterable of runner events called as `runner(initiative, evidence, portfolio=...)`; `NodeCompleteEvent(node, report)` and `FinishedEvent(...)` from `productagents.runner`; `AnalystReport`, `Recommendation`, `Evidence` from `productagents.schemas`.
- Produces: a one-line membership guard so a `NodeCompleteEvent` whose `node` is not a `_PANELS` key is skipped instead of raising `NoMatches`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tui.py` (keep existing tests; `partial`, `pytest`, `ProductAgentsApp` are already imported at the top of the file):

```python
async def test_completion_event_without_panel_is_ignored(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.runner import FinishedEvent, NodeCompleteEvent
    from productagents.schemas import AnalystReport, Evidence, Recommendation

    async def fake_runner(initiative, evidence, *, portfolio=None):
        # A completion event for a node id that has no matching panel must be
        # skipped, not crash the worker with NoMatches before the run finishes.
        yield NodeCompleteEvent(
            node="aggregator",
            report=AnalystReport(
                analyst="aggregator",
                role="Aggregator",
                findings=["x"],
                signals=[],
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
        fake_runner, evidence, recorder=lambda r: None, reader=lambda: []
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        strat_text = str(pilot.app.query_one("#strategist").content)

    # The unknown-node completion was skipped, so the run reached FinishedEvent
    # and rendered the recommendation.
    assert "Build it" in strat_text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tui.py -k completion_event_without_panel -v`
Expected: FAIL — without the guard, `self.query_one("#aggregator", Static)` raises `NoMatches` inside the worker before the `FinishedEvent` is processed, so the strategist panel never renders the recommendation (the assertion fails, or the failure surfaces as the `NoMatches` worker error).

- [ ] **Step 3: Add the guard**

In `src/productagents/tui/app.py`, find the `NodeCompleteEvent` branch in the `_run` worker:

```python
            elif isinstance(event, NodeCompleteEvent):
                report = event.report
                body = "\n".join(f"• {f}" for f in report.findings) or "(no findings)"
                self.query_one(f"#{event.node}", Static).update(body)
```

Replace it with a guarded version (mirroring the `ProgressEvent` branch directly above it):

```python
            elif isinstance(event, NodeCompleteEvent):
                if event.node in _PANELS:
                    report = event.report
                    body = (
                        "\n".join(f"• {f}" for f in report.findings)
                        or "(no findings)"
                    )
                    self.query_one(f"#{event.node}", Static).update(body)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_tui.py -k completion_event_without_panel -v`
Expected: PASS — the unknown-node completion is skipped and the recommendation renders.

- [ ] **Step 5: Run the full TUI test file**

Run: `uv run pytest tests/test_tui.py -v`
Expected: PASS — existing panel-rendering tests still pass (every real analyst node id is in `_PANELS`, so the guard never skips a legitimate panel update).

- [ ] **Step 6: Commit**

```bash
git add src/productagents/tui/app.py tests/test_tui.py
git commit -m "fix: guard NodeCompleteEvent handler against non-panel node ids"
```

---

### Task 2: Consolidate the analyst-node test imports

**Files:**
- Modify: `tests/test_analysts.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a single top-of-file import block; the three mid-file `# noqa: E402` imports for `market_node`, `business_node`, and `technical_node` are removed.

- [ ] **Step 1: Confirm the current state (the noqa suppressions)**

Run: `grep -n "noqa: E402" tests/test_analysts.py`
Expected: three matches — the `market_node`, `business_node`, and `technical_node` imports placed between test functions (roughly lines 65, 94, 123).

- [ ] **Step 2: Move the three imports into the top block**

In `tests/test_analysts.py`, the current top import block is:

```python
import pytest

from productagents.agents.customer_research import customer_research_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.schemas import AnalystFindings, Evidence, Initiative
from tests.fakes import FakeChatModel
```

Replace it with the consolidated, alphabetically-ordered block (adds the three analyst imports, no `# noqa`):

```python
import pytest

from productagents.agents.business import business_node
from productagents.agents.customer_research import customer_research_node
from productagents.agents.market import market_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.technical import technical_node
from productagents.schemas import AnalystFindings, Evidence, Initiative
from tests.fakes import FakeChatModel
```

- [ ] **Step 3: Delete the three mid-file import lines**

Remove these three lines from where they sit between the test functions (do not remove anything else):

```python
from productagents.agents.market import market_node  # noqa: E402
```

```python
from productagents.agents.business import business_node  # noqa: E402
```

```python
from productagents.agents.technical import technical_node  # noqa: E402
```

(After removal, the blank lines they left behind should collapse so there are no triple blank lines between test functions; ruff format in Step 4 will normalize spacing.)

- [ ] **Step 4: Verify lint is clean without the suppressions**

Run: `uv run ruff check tests/test_analysts.py && uv run ruff format --check tests/test_analysts.py`
Expected: PASS with no `E402` (module-level import not at top of file) findings and no formatting diff. (If `ruff format --check` reports a diff from collapsed blank lines, run `uv run ruff format tests/test_analysts.py` and re-run the check.)

- [ ] **Step 5: Run the analyst tests**

Run: `uv run pytest tests/test_analysts.py -v`
Expected: PASS — all ten analyst tests still pass; only import placement changed, no behavior changed.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: PASS — full suite green.

- [ ] **Step 7: Commit**

```bash
git add tests/test_analysts.py
git commit -m "refactor: hoist analyst-node test imports to top of file"
```

---

## Self-Review

**1. Spec coverage** (against the two PR #10 review follow-ups):

- Guard the `NodeCompleteEvent` handler with `if event.node in _PANELS:` for symmetry with the `ProgressEvent` branch → Task 1 (test + one-line guard). ✓
- Consolidate the three `# noqa: E402` analyst-node test imports to the top of `tests/test_analysts.py` and drop the suppressions → Task 2 (move + delete + ruff verification). ✓

**2. Placeholder scan**

No "TBD"/"TODO"/"handle edge cases"/"similar to Task N". Every code step shows the exact code to add or remove, and every verification step shows the exact command and expected result. ✓

**3. Type consistency**

- The Task 1 test constructs `NodeCompleteEvent(node, report)` and `FinishedEvent(recommendation, reports, debate, risks, governance)` — matching the dataclasses in `runner.py` on post-#10 `main` (the Global Constraints note covers the one-field difference if outcome-injection was run first). ✓
- The guard uses the module-level `_PANELS` dict already referenced by the `ProgressEvent` branch and the `on_mount`/`on_input_submitted` loops — same name, same semantics. ✓
- Task 2 changes only import placement; the imported names (`business_node`, `market_node`, `technical_node`) are unchanged and already used by the existing tests. ✓

No gaps found.
