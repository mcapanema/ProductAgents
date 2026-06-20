# Human-in-the-Loop Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Product Portfolio Manager an *advisor* rather than the final authority — pause the graph after governance, present its recommended verdict to a human in the TUI, and record the human's approve / reject / request-analysis as the binding decision.

**Architecture:** The LLM `governance` node is unchanged — it still produces a `GovernanceVerdict`, but that verdict is now treated as *advisory*. A new model-free `human_approval` node runs after it and calls LangGraph's `interrupt()` to pause the graph; the runner surfaces the interrupt through an injected `approver` callback, the TUI shows a modal, and the human's `HumanDecision` is fed back via `Command(resume=...)`. The `human_approval` node assembles the *final* `GovernanceVerdict` (carrying the human's choice plus the AI's advice for traceability). Human-in-the-loop is opt-in via a `build_graph(model, human_in_the_loop=True)` flag that adds the node and a checkpointer; the default graph (used by most tests) is byte-for-byte unchanged.

**Tech Stack:** Python ≥ 3.14, uv, LangGraph 1.2.6 (`interrupt`, `Command`, `InMemorySaver`), Textual (`ModalScreen`, `push_screen_wait`), Pydantic, pytest (offline with `FakeChatModel`).

## Global Constraints

- Python ≥ 3.14; dependency manager is **uv** (`uv run pytest`, `uv run productagents`). One line each below applies to every task.
- **Nodes degrade, never crash.** Wrap fallible work so one failure can't abort the graph; the human-gate path must still yield a usable verdict if the advisory is missing.
- **Streaming from nodes** uses `productagents.agents._stream.get_writer()`, never `langgraph.config.get_stream_writer()` directly.
- **Tests are fully offline.** Use `tests.fakes.FakeChatModel` (maps a schema class → the instance/Exception its `with_structured_output(schema).ainvoke()` returns). No network, no API key.
- **Backward compatibility:** new `GovernanceVerdict` fields MUST have defaults so existing `decisions.jsonl` records and all current tests still load and pass. The default `build_graph(model)` (no flag) MUST remain identical to today.
- Coverage gate is 90% (`pytest` auto-runs `--cov`); keep the suite green.
- LangGraph fan-in gotcha (observed in this repo): adding a cross-superstep explicit edge into a node that already has a fan-in can double-fire it. The new `human_approval` node is a **simple linear chain** (`governance → human_approval → END`), which avoids this — do not add it as a parallel fan-in.

---

## File Structure

**Modified:**
- `src/productagents/schemas.py` — add provenance fields to `GovernanceVerdict`; add `HumanDecision`.
- `src/productagents/graph.py` — `build_graph(model, *, human_in_the_loop=False)`: conditional node + checkpointer.
- `src/productagents/runner.py` — `FinalVerdictEvent`; `approver` param; interrupt-detect / resume loop.
- `src/productagents/tui/app.py` — build HITL graph, pass `approver=self._ask_human`, render `FinalVerdictEvent`.

**Created:**
- `src/productagents/agents/human_approval.py` — the `human_approval` node + pure `_final_verdict` helper.
- `src/productagents/tui/approval.py` — `ApprovalScreen` modal.
- `tests/test_human_approval.py`, `tests/test_approval_tui.py` — new tests (other tests extended in place).

---

### Task 1: Schema — advisory provenance on `GovernanceVerdict` + `HumanDecision`

**Files:**
- Modify: `src/productagents/schemas.py:106-111` (the `GovernanceVerdict` class)
- Modify: `src/productagents/schemas.py` (add `HumanDecision` after `GovernanceVerdict`)
- Test: `tests/test_schemas.py`

**Interfaces:**
- Produces:
  - `GovernanceVerdict(verdict: str, rationale: str, failed: bool = False, decided_by: str = "ai", advisory_verdict: str | None = None, advisory_rationale: str | None = None)`
  - `HumanDecision(verdict: str, rationale: str = "")`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_schemas.py`:

```python
def test_governance_verdict_defaults_are_ai_authored():
    from productagents.schemas import GovernanceVerdict

    v = GovernanceVerdict(verdict="approve", rationale="worth it")
    assert v.decided_by == "ai"
    assert v.advisory_verdict is None
    assert v.advisory_rationale is None
    assert v.failed is False


def test_governance_verdict_records_human_override():
    from productagents.schemas import GovernanceVerdict

    v = GovernanceVerdict(
        verdict="reject",
        rationale="no capacity this quarter",
        decided_by="human",
        advisory_verdict="approve",
        advisory_rationale="strong demand",
    )
    assert v.decided_by == "human"
    assert v.advisory_verdict == "approve"


def test_human_decision_defaults_blank_rationale():
    from productagents.schemas import HumanDecision

    d = HumanDecision(verdict="approve")
    assert d.verdict == "approve"
    assert d.rationale == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas.py -k "governance_verdict or human_decision" -v`
Expected: FAIL — `ImportError`/`AttributeError` for `HumanDecision` and unexpected-keyword for `decided_by`.

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/schemas.py`, replace the `GovernanceVerdict` class:

```python
class GovernanceVerdict(BaseModel):
    """One assembled governance verdict plus a failure flag set by the node.

    In human-in-the-loop runs this carries the *final* (human) decision, with the
    AI's advisory recommendation preserved for traceability. In autonomous runs
    `decided_by` stays "ai" and the advisory fields stay None.
    """

    verdict: str
    rationale: str
    failed: bool = False
    decided_by: str = "ai"
    advisory_verdict: str | None = None
    advisory_rationale: str | None = None
```

Then add, immediately after `GovernanceVerdict`:

```python
class HumanDecision(BaseModel):
    """A human reviewer's final governance choice, fed back to resume the graph."""

    verdict: str = Field(
        description="One of 'approve', 'reject', or 'request_analysis'."
    )
    rationale: str = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_schemas.py -k "governance_verdict or human_decision" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `uv run pytest -q`
Expected: all pass (the new fields are defaulted, so existing records still load).

- [ ] **Step 6: Commit**

```bash
git add src/productagents/schemas.py tests/test_schemas.py
git commit -m "feat: add advisory provenance to GovernanceVerdict and HumanDecision schema"
```

---

### Task 2: The `human_approval` node + pure `_final_verdict` helper

**Files:**
- Create: `src/productagents/agents/human_approval.py`
- Test: `tests/test_human_approval.py`

**Interfaces:**
- Consumes: `state["governance"]` — the advisory `GovernanceVerdict` produced by the existing `governance` node (may be absent/None).
- Produces:
  - `_final_verdict(advisory: GovernanceVerdict | None, decision: dict) -> GovernanceVerdict` — pure, unit-testable. `decision` is the resume payload `{"verdict": str, "rationale": str}`.
  - `async human_approval_node(state: dict) -> dict` — calls `interrupt({"advisory": <dump or None>})`, builds the final verdict via `_final_verdict`, emits a custom `{"node": "human_approval", "final_verdict": ...}` event, returns `{"governance": <final verdict>}`.
  - Module constant `NODE_ID = "human_approval"`.

> **Why a separate helper:** `interrupt()` raises when called outside an active graph run, so the node can't be unit-tested by direct call. The verdict-assembly logic lives in `_final_verdict`, which is tested directly; the node is exercised end-to-end via the graph in Tasks 3–4.

> **Why no LLM call in this node:** on resume, LangGraph re-executes the interrupted node from the top. Keeping this node model-free and side-effect-free *before* the `interrupt()` call means resumption is cheap and the only `writer` emission happens once, after resume.

- [ ] **Step 1: Write the failing test**

Create `tests/test_human_approval.py`:

```python
from productagents.agents.human_approval import _final_verdict
from productagents.schemas import GovernanceVerdict


def _advisory(verdict="approve", rationale="strong demand"):
    return GovernanceVerdict(verdict=verdict, rationale=rationale)


def test_final_verdict_records_human_choice_and_advisory():
    final = _final_verdict(
        _advisory(),
        {"verdict": "reject", "rationale": "no capacity this quarter"},
    )
    assert final.verdict == "reject"
    assert final.rationale == "no capacity this quarter"
    assert final.decided_by == "human"
    assert final.advisory_verdict == "approve"
    assert final.advisory_rationale == "strong demand"
    assert final.failed is False


def test_final_verdict_falls_back_to_advisory_rationale_when_note_blank():
    final = _final_verdict(_advisory(rationale="resources well spent"), {"verdict": "approve", "rationale": ""})
    assert final.verdict == "approve"
    assert final.rationale == "resources well spent"


def test_final_verdict_tolerates_missing_advisory():
    final = _final_verdict(None, {"verdict": "approve", "rationale": "ship it"})
    assert final.verdict == "approve"
    assert final.rationale == "ship it"
    assert final.advisory_verdict is None
    assert final.advisory_rationale is None
    assert final.decided_by == "human"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_human_approval.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.agents.human_approval'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/productagents/agents/human_approval.py`:

```python
"""Human approval node: a human reviewer is the final governance authority.

Runs immediately after the LLM `governance` node, whose verdict is treated as
*advisory*. This node pauses the graph with LangGraph's `interrupt()`, surfacing
the advisory verdict to a human (via the runner's `approver` callback and the
TUI). The human's `HumanDecision` is fed back through `Command(resume=...)` and
becomes the binding `GovernanceVerdict` recorded for the decision. Added to the
graph only when `build_graph(model, human_in_the_loop=True)`.
"""

from langgraph.types import interrupt

from productagents.agents._stream import get_writer
from productagents.schemas import GovernanceVerdict

NODE_ID = "human_approval"


def _final_verdict(
    advisory: GovernanceVerdict | None, decision: dict
) -> GovernanceVerdict:
    """Assemble the binding verdict from the human's decision plus the AI advisory."""
    rationale = decision.get("rationale") or ""
    if not rationale and advisory is not None:
        rationale = advisory.rationale
    return GovernanceVerdict(
        verdict=decision["verdict"],
        rationale=rationale,
        decided_by="human",
        advisory_verdict=advisory.verdict if advisory else None,
        advisory_rationale=advisory.rationale if advisory else None,
    )


async def human_approval_node(state: dict) -> dict:
    advisory = state.get("governance")
    payload = {"advisory": advisory.model_dump() if advisory else None}
    # interrupt() pauses the graph; on resume it returns the Command(resume=...) value.
    decision = interrupt(payload)
    verdict = _final_verdict(advisory, decision)
    writer = get_writer()
    writer({"node": NODE_ID, "final_verdict": verdict.model_dump()})
    return {"governance": verdict}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_human_approval.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/human_approval.py tests/test_human_approval.py
git commit -m "feat: add human_approval node with advisory-aware final verdict"
```

---

### Task 3: Wire the HITL path into the graph (opt-in flag + checkpointer)

**Files:**
- Modify: `src/productagents/graph.py:45-77` (the `build_graph` function)
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: `human_approval_node` (Task 2), `InMemorySaver`.
- Produces: `build_graph(model, *, human_in_the_loop: bool = False)`. When `False` (default): identical to today, `governance → END`, no checkpointer. When `True`: adds `human_approval` node, `governance → human_approval → END`, compiled with `InMemorySaver()`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_graph.py` (reuses the existing module-level `_model` helper):

```python
def test_default_graph_has_no_human_approval_node():
    graph = build_graph(_model())
    assert "human_approval" not in graph.nodes


def test_human_in_the_loop_graph_adds_human_approval_node():
    graph = build_graph(_model(), human_in_the_loop=True)
    assert "human_approval" in graph.nodes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_graph.py -k human -v`
Expected: FAIL — `TypeError: build_graph() got an unexpected keyword argument 'human_in_the_loop'`.

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/graph.py`, add imports near the top (with the other agent imports and after the langgraph import):

```python
from langgraph.checkpoint.memory import InMemorySaver
```

```python
from productagents.agents.human_approval import human_approval_node
```

Change the signature and the tail of `build_graph`. Replace the existing final edge line `graph.add_edge("governance", END)` and the `return graph.compile()` with the conditional below, and update the `def`:

```python
def build_graph(model, *, human_in_the_loop: bool = False):
    """Compile the decision graph using the injected chat model.

    When `human_in_the_loop` is True, a `human_approval` node is appended after
    `governance` (whose verdict becomes advisory) and the graph is compiled with
    an in-memory checkpointer so it can pause on `interrupt()` and resume.
    """
```

(Leave every `add_node`/`add_edge` from `START` through `graph.add_edge("risk", "governance")` exactly as-is.) Then, in place of the old `graph.add_edge("governance", END)` / `return graph.compile()`:

```python
    if human_in_the_loop:
        graph.add_node("human_approval", human_approval_node)
        graph.add_edge("governance", "human_approval")
        graph.add_edge("human_approval", END)
        return graph.compile(checkpointer=InMemorySaver())

    graph.add_edge("governance", END)
    return graph.compile()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_graph.py -k human -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full graph test file to confirm the default path is unchanged**

Run: `uv run pytest tests/test_graph.py -q`
Expected: all pass — including the pre-existing `test_graph_runs_through_governance` (default graph, no checkpointer).

- [ ] **Step 6: Commit**

```bash
git add src/productagents/graph.py tests/test_graph.py
git commit -m "feat: add opt-in human_in_the_loop flag to build_graph"
```

---

### Task 4: Runner — interrupt detection, `approver` callback, resume loop, `FinalVerdictEvent`

**Files:**
- Modify: `src/productagents/runner.py` (imports, new dataclass, `run_decision`)
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `Command` and the `__interrupt__` chunk shape `{"__interrupt__": (Interrupt(value={"advisory": <GovernanceVerdict dump | None>}),)}`; the `human_approval` node's custom `{"final_verdict": <GovernanceVerdict dump>}`; `GovernanceVerdict`, `HumanDecision` schemas.
- Produces:
  - `FinalVerdictEvent(verdict: str, rationale: str, decided_by: str)` dataclass.
  - `run_decision(graph, initiative, evidence, portfolio=None, outcomes=None, *, approver=None)` where `approver: Callable[[GovernanceVerdict | None], Awaitable[HumanDecision]] | None`. On interrupt it awaits `approver(advisory)`; with no approver it auto-accepts the advisory. `FinishedEvent.governance` is the **final** verdict in HITL runs.

> **Verified behavior (LangGraph 1.2.6):** `astream(input, config, stream_mode=["updates","custom"])` yields `{"__interrupt__": (...)}` in the `updates` stream when the graph pauses, then the stream ends. Re-calling `astream(Command(resume=value), config, ...)` on the same `thread_id` resumes; the resume value becomes `interrupt()`'s return. Passing a `config` with a `thread_id` to a graph compiled *without* a checkpointer is harmless (ignored), so the runner uses one uniformly.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_runner.py`. The existing `_graph()`/`_inputs()` helpers build a default graph; add HITL-specific helpers and tests:

```python
from productagents.runner import FinalVerdictEvent  # add to the existing imports block
from productagents.schemas import HumanDecision  # add to the existing imports block


def _hitl_graph():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            ),
            RiskFinding: RiskFinding(level="low", rationale="cheap"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="resources well spent"
            ),
        }
    )
    return build_graph(model, human_in_the_loop=True)


async def test_run_decision_human_override_becomes_final_verdict(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = _hitl_graph()
    initiative, evidence = _inputs()
    seen_advisory = []

    async def approver(advisory):
        seen_advisory.append(advisory)
        return HumanDecision(verdict="reject", rationale="no capacity")

    events = [
        e
        async for e in run_decision(graph, initiative, evidence, approver=approver)
    ]

    # The approver was shown the AI's advisory verdict.
    assert len(seen_advisory) == 1
    assert seen_advisory[0].verdict == "approve"

    finals = [e for e in events if isinstance(e, FinalVerdictEvent)]
    assert len(finals) == 1
    assert finals[0].verdict == "reject"
    assert finals[0].decided_by == "human"

    finished = [e for e in events if isinstance(e, FinishedEvent)][0]
    assert finished.governance.verdict == "reject"
    assert finished.governance.decided_by == "human"
    assert finished.governance.advisory_verdict == "approve"


async def test_run_decision_without_approver_auto_accepts_advisory(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = _hitl_graph()
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    finished = [e for e in events if isinstance(e, FinishedEvent)][0]
    assert finished.governance.verdict == "approve"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_runner.py -k "human_override or auto_accepts" -v`
Expected: FAIL — `ImportError: cannot import name 'FinalVerdictEvent'`.

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/runner.py`:

(a) Extend the imports at the top of the file:

```python
from uuid import uuid4

from langgraph.types import Command
```

and add `GovernanceVerdict` is already imported; also import `HumanDecision` in the existing schemas import block:

```python
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    DecisionRecord,
    Evidence,
    GovernanceVerdict,
    HumanDecision,
    Initiative,
    OutcomeRecord,
    Recommendation,
    RiskAssessment,
)
```

(b) Add the new event dataclass next to the others (e.g. after `GovernanceVerdictEvent`):

```python
@dataclass
class FinalVerdictEvent:
    verdict: str
    rationale: str
    decided_by: str
```

(c) Add `FinalVerdictEvent` to the `AsyncIterator[...]` union in `run_decision`'s return annotation (insert it after `GovernanceVerdictEvent`):

```python
) -> AsyncIterator[
    ProgressEvent
    | NodeCompleteEvent
    | DebateTurnEvent
    | RiskAssessmentEvent
    | GovernanceVerdictEvent
    | FinalVerdictEvent
    | RecallEvent
    | FinishedEvent
]:
```

(d) Add the `approver` keyword to the signature:

```python
async def run_decision(
    graph,
    initiative: Initiative,
    evidence: Evidence,
    portfolio: list[DecisionRecord] | None = None,
    outcomes: list[OutcomeRecord] | None = None,
    *,
    approver=None,
) -> AsyncIterator[
```

(e) Replace the streaming section. Keep the `initial_state` and `collected_*` setup exactly as-is. Replace the single `async for mode, chunk in graph.astream(...)` block (lines that start at `async for mode, chunk in graph.astream(` through the end of the `elif mode == "updates":` handling, i.e. everything *before* the final `yield FinishedEvent(...)`) with this resume loop:

```python
    config = {"configurable": {"thread_id": uuid4().hex}}
    stream_input: dict | Command = initial_state

    while True:
        pending_interrupt: dict | None = None
        async for mode, chunk in graph.astream(
            stream_input, config, stream_mode=["updates", "custom"]
        ):
            if mode == "custom":
                if "turn" in chunk:
                    turn = chunk["turn"]
                    yield DebateTurnEvent(
                        round=turn["round"],
                        side=turn["side"],
                        argument=turn["argument"],
                    )
                elif "assessment" in chunk:
                    a = chunk["assessment"]
                    yield RiskAssessmentEvent(
                        reviewer=a["reviewer"],
                        role=a["role"],
                        level=a["level"],
                        rationale=a["rationale"],
                    )
                elif "final_verdict" in chunk:
                    fv = chunk["final_verdict"]
                    yield FinalVerdictEvent(
                        verdict=fv["verdict"],
                        rationale=fv["rationale"],
                        decided_by=fv["decided_by"],
                    )
                elif "verdict" in chunk:
                    v = chunk["verdict"]
                    yield GovernanceVerdictEvent(
                        verdict=v["verdict"],
                        rationale=v["rationale"],
                    )
                else:
                    yield ProgressEvent(
                        node=chunk.get("node", ""), message=chunk.get("status", "")
                    )
            elif mode == "updates":
                if "__interrupt__" in chunk:
                    pending_interrupt = chunk["__interrupt__"][0].value
                    continue
                for node_name, node_state in chunk.items():
                    if not node_state:
                        continue
                    for report in node_state.get("reports", []) or []:
                        collected_reports.append(report)
                        yield NodeCompleteEvent(node=node_name, report=report)
                    if node_state.get("debate"):
                        collected_debate = node_state["debate"]
                    if node_state.get("risks"):
                        collected_risks = node_state["risks"]
                    if "prior_lessons" in node_state:
                        collected_lessons = node_state["prior_lessons"]
                        yield RecallEvent(lessons=collected_lessons)
                    if node_state.get("recommendation") is not None:
                        recommendation = node_state["recommendation"]
                    if node_state.get("governance") is not None:
                        governance = node_state["governance"]

        if pending_interrupt is None:
            break

        advisory_dump = pending_interrupt.get("advisory")
        advisory = GovernanceVerdict(**advisory_dump) if advisory_dump else None
        if approver is not None:
            decision = await approver(advisory)
        else:
            decision = HumanDecision(
                verdict=advisory.verdict if advisory else "approve",
                rationale=advisory.rationale if advisory else "",
            )
        stream_input = Command(resume=decision.model_dump())
```

(Note: `final_verdict` is checked *before* `verdict` because the human_approval node's payload key is distinct; ordering also keeps the advisory `verdict` event mapping intact.)

Update the docstring's stream description to mention the governance `final_verdict` chunk and interrupt/resume (one sentence): "`custom` chunks also carry a governance `final_verdict` dict after human approval; an `__interrupt__` update pauses the run until the injected `approver` returns a `HumanDecision`, which resumes the graph via `Command(resume=...)`."

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_runner.py -k "human_override or auto_accepts" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the whole runner suite to confirm the non-HITL path is unchanged**

Run: `uv run pytest tests/test_runner.py -q`
Expected: all pass — the existing `test_run_decision_emits_all_event_types` (default graph) still works; `approver` defaults to None and no interrupt fires.

- [ ] **Step 6: Commit**

```bash
git add src/productagents/runner.py tests/test_runner.py
git commit -m "feat: runner surfaces governance interrupt and resumes with human decision"
```

---

### Task 5: TUI — `ApprovalScreen` modal + app wiring + `FinalVerdictEvent` rendering

**Files:**
- Create: `src/productagents/tui/approval.py`
- Modify: `src/productagents/tui/app.py` (imports, `_ask_human`, runner call, `FinalVerdictEvent` branch, `_build_app`)
- Test: `tests/test_approval_tui.py`; extend `tests/test_tui.py` is **not** required (its injected non-HITL runner stays valid).

**Interfaces:**
- Consumes: `FinalVerdictEvent` (Task 4); `GovernanceVerdict`, `HumanDecision` (Task 1); `run_decision` `approver` param.
- Produces:
  - `ApprovalScreen(ModalScreen[HumanDecision])` — shows the advisory verdict, an optional note `Input#note`, and three buttons (`#approve`, `#reject`, `#request_analysis`); `dismiss(HumanDecision(verdict=<button id>, rationale=<note>))` on press.
  - `ProductAgentsApp._ask_human(self, advisory) -> HumanDecision` — `await self.push_screen_wait(ApprovalScreen(advisory))`.
  - `_build_app()` now builds `build_graph(model, human_in_the_loop=True)`.

> **Verified (Textual):** `push_screen_wait` returns the `Screen.dismiss(value)` result and may only be called from a worker. `_run` is `@work(exclusive=True)`, and `_ask_human` is awaited *inside* `run_decision`, which is driven by the `async for` in `_run` — so it runs in worker context.

- [ ] **Step 1: Write the failing test**

Create `tests/test_approval_tui.py`. It drives a *real* HITL graph end-to-end through the app, lets the graph reach the interrupt (which pushes `ApprovalScreen`), then clicks a button:

```python
from functools import partial

from productagents.graph import build_graph
from productagents.runner import run_decision
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    Recommendation,
    RiskFinding,
)
from productagents.tui.app import ProductAgentsApp
from productagents.tui.approval import ApprovalScreen
from tests.fakes import FakeChatModel


def _hitl_runner_and_evidence():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: Recommendation(
                recommendation="Build SSO now",
                confidence=0.81,
                rationale="strong demand",
                expected_outcomes=["enterprise unblock"],
            ),
            RiskFinding: RiskFinding(level="medium", rationale="some delivery risk"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="best use of resources"
            ),
        }
    )
    graph = build_graph(model, human_in_the_loop=True)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    return partial(run_decision, graph), evidence


async def test_human_reject_overrides_advisory_and_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, evidence = _hitl_runner_and_evidence()
    recorded = []

    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        # Let the graph run to the governance interrupt, which pushes the modal.
        for _ in range(50):
            await pilot.pause()
            if isinstance(pilot.app.screen, ApprovalScreen):
                break
        assert isinstance(pilot.app.screen, ApprovalScreen)

        pilot.app.screen.query_one("#note").value = "No capacity this quarter."
        await pilot.click("#reject")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()

        gov_text = str(pilot.app.query_one("#governance").content)
        assert "reject" in gov_text
        assert "human" in gov_text

    assert len(recorded) == 1
    verdict = recorded[0].governance
    assert verdict.verdict == "reject"
    assert verdict.decided_by == "human"
    assert verdict.advisory_verdict == "approve"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_approval_tui.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.tui.approval'`.

- [ ] **Step 3a: Create the modal screen**

Create `src/productagents/tui/approval.py`:

```python
"""Approval mode: a human reviewer makes the final governance call.

Shown when a human-in-the-loop run pauses after the Portfolio Manager produces
its advisory verdict. The reviewer approves, rejects, or requests further
analysis (with an optional note); the choice is returned to the graph as a
`HumanDecision` via `Screen.dismiss`.
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from productagents.schemas import GovernanceVerdict, HumanDecision


class ApprovalScreen(ModalScreen[HumanDecision]):
    """Present the advisory verdict and capture the human's final decision."""

    def __init__(self, advisory: GovernanceVerdict | None):
        super().__init__()
        self._advisory = advisory

    def compose(self) -> ComposeResult:
        rec = self._advisory.verdict if self._advisory else "n/a"
        rationale = self._advisory.rationale if self._advisory else ""
        yield Static(
            f"Portfolio Manager recommends: [b]{rec}[/b]\n\n{rationale}",
            id="advisory",
        )
        yield Input(placeholder="Optional note for the record…", id="note")
        yield Button("Approve", id="approve", variant="success")
        yield Button("Reject", id="reject", variant="error")
        yield Button("Request analysis", id="request_analysis")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        note = self.query_one("#note", Input).value.strip()
        self.dismiss(HumanDecision(verdict=event.button.id, rationale=note))
```

- [ ] **Step 3b: Wire the app**

In `src/productagents/tui/app.py`:

Add to the `runner` import block:

```python
from productagents.runner import (
    DebateTurnEvent,
    FinalVerdictEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    NodeCompleteEvent,
    ProgressEvent,
    RecallEvent,
    RiskAssessmentEvent,
    run_decision,
)
```

Add the approval screen import (next to the reflection screen import):

```python
from productagents.tui.approval import ApprovalScreen
```

Add the `_ask_human` method (e.g. just after `action_reflect`):

```python
    async def _ask_human(self, advisory):
        """Pause for a human governance decision; returns a HumanDecision."""
        return await self.push_screen_wait(ApprovalScreen(advisory))
```

Pass the approver into the runner call inside `_run` (extend the existing call):

```python
        async for event in self._runner(
            initiative,
            self._evidence,
            portfolio=portfolio,
            outcomes=outcomes,
            approver=self._ask_human,
        ):
```

Render `FinalVerdictEvent` — add this branch in the event loop, right after the `GovernanceVerdictEvent` branch:

```python
            elif isinstance(event, FinalVerdictEvent):
                self.query_one("#governance", Static).update(
                    f"[b]FINAL ({event.decided_by}): {event.verdict}[/b]\n\n"
                    f"{event.rationale}"
                )
```

Build the HITL graph in `_build_app`:

```python
    graph = build_graph(model, human_in_the_loop=True)
```

- [ ] **Step 4: Run the new test to verify it passes**

Run: `uv run pytest tests/test_approval_tui.py -v`
Expected: PASS.

- [ ] **Step 5: Confirm the existing TUI tests still pass**

Run: `uv run pytest tests/test_tui.py -q`
Expected: all pass — the injected non-HITL runner never interrupts, so `approver=self._ask_human` is passed but never invoked, and `FinalVerdictEvent` never fires.

- [ ] **Step 6: Commit**

```bash
git add src/productagents/tui/approval.py src/productagents/tui/app.py tests/test_approval_tui.py
git commit -m "feat: add human approval modal and wire it into the TUI"
```

---

### Task 6: Documentation — README + CLAUDE.md

**Files:**
- Modify: `README.md:447-467` (the "Running the Slice" section)
- Modify: `CLAUDE.md` (the architecture summary diagram + the `graph.py`/`runner.py`/`tui` bullets)

**Interfaces:** none (docs only). No test; verification is the full suite plus a manual re-read.

- [ ] **Step 1: Update the README slice description**

In `README.md`, update the slice paragraph (around lines 447–458) so the governance sentence reads that the Portfolio Manager now produces an **advisory** verdict and a **human** makes the binding approve / reject / request-analysis call in the TUI. Add a short sentence:

```markdown
The Product Portfolio Manager's verdict is now *advisory*: each run pauses after
governance and asks a human to make the binding call — approve, reject, or
request further analysis (with an optional note) — directly in the TUI. The
recorded decision preserves both the human's choice and the AI's recommendation
for traceability.
```

- [ ] **Step 2: Update CLAUDE.md**

In `CLAUDE.md`:

(a) Extend the architecture diagram's tail so it reads:

```
… → strategist → risk → governance (advisory) → human_approval → decisions.jsonl
```

(b) Update the `graph.py` description to note that `build_graph(model, human_in_the_loop=True)` appends a `human_approval` node after `governance` and compiles with an `InMemorySaver` checkpointer so the graph can `interrupt()` and resume.

(c) Update the `runner.py` bullet to note that `run_decision` accepts an `approver` callback: on a governance `__interrupt__` it awaits `approver(advisory)` for a `HumanDecision` and resumes via `Command(resume=...)`, emitting a `FinalVerdictEvent`.

(d) Update the `tui/app.py` bullet to note the `ApprovalScreen` modal (`tui/approval.py`) shown via `push_screen_wait` from the worker.

- [ ] **Step 3: Run the full suite as a final gate**

Run: `uv run pytest -q`
Expected: all pass; coverage ≥ 90%.

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document human-in-the-loop governance"
```

---

## Self-Review

**Spec coverage** (the chosen direction — "human-in-the-loop governance: a LangGraph interrupt pauses the Portfolio Manager for a real human approve / reject / request-more in the TUI, instead of the LLM auto-deciding"):
- Interrupt-based pause → Task 2 (`interrupt()` in `human_approval_node`) + Task 3 (checkpointer/wiring) + Task 4 (runner detect/resume). ✅
- Human approve / reject / request-analysis → Task 5 (`ApprovalScreen` three buttons mapped to verdicts). ✅
- "instead of the LLM auto-deciding" → governance verdict reclassified as advisory; final verdict is `decided_by="human"` (Tasks 1, 2, 4). ✅
- Surfaced live in the TUI → Task 5 (modal + `FinalVerdictEvent` rendering). ✅
- Recorded to `decisions.jsonl` → existing `_recorder` path persists `FinishedEvent.governance`, now the human verdict with advisory provenance (Tasks 1, 4). ✅
- Opt-in / backward compatible → default `build_graph(model)` unchanged; new `GovernanceVerdict` fields defaulted (Tasks 1, 3); existing suites re-run in Tasks 3/4/5. ✅

**Placeholder scan:** every code step shows complete code; no "TBD"/"add error handling"/"similar to". The node degrades when the advisory is absent (`_final_verdict(None, …)`) and when no approver is supplied (auto-accept), satisfying the never-crash constraint. ✅

**Type consistency:** `GovernanceVerdict` fields (`decided_by`, `advisory_verdict`, `advisory_rationale`) named identically in schemas (Task 1), the node helper (Task 2), and runner/TUI consumption (Tasks 4–5). `HumanDecision(verdict, rationale)` consistent across node resume payload, runner, and `ApprovalScreen.dismiss`. `FinalVerdictEvent(verdict, rationale, decided_by)` defined in Task 4 and consumed unchanged in Task 5. The interrupt payload key `"advisory"` and the custom event key `"final_verdict"` match between `human_approval_node` (Task 2) and the runner (Task 4). `human_approval` node id is consistent across Tasks 2/3/5. ✅
```
