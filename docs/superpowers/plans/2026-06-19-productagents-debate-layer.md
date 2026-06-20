# ProductAgents Debate Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insert a structured Advocate-vs-Skeptic debate between the analyst team and the strategist, stream each turn live into the TUI, feed the transcript to the strategist, and persist the full transcript in every decision record.

**Architecture:** A single `debate_node` runs between the parallel analysts (fan-in) and the strategist. It loops for a configurable number of rounds; each round the Opportunity Advocate argues, then the Opportunity Skeptic rebuts, each seeing the analyst reports and the debate so far. The node emits one custom stream event per turn (for live TUI rendering) and returns the structured transcript in graph state. The strategist reads the transcript alongside the analyst reports, and the TUI records it in the `DecisionRecord`.

**Tech Stack:** Python 3.14, UV, LangGraph, LangChain (`init_chat_model`), Pydantic v2, Textual, pytest + pytest-asyncio.

## Global Constraints

- Python `>=3.14`; UV only. Run all commands with `uv run ...` from the repo root.
- All LLM access flows through an injected model; agents never construct a provider client. Debate agents produce output via `model.with_structured_output(DebateArgument)`.
- Debate rounds are configured by env `PRODUCTAGENTS_DEBATE_ROUNDS` (positive integer, default `2`). Invalid or non-positive values fall back to `2`.
- Each round runs the Advocate first, then the Skeptic. A run of `R` rounds therefore produces exactly `2 * R` `DebateTurn`s, in order `(round=1, advocate), (round=1, skeptic), (round=2, advocate), …`.
- `side` is exactly the string `"advocate"` or `"skeptic"`.
- The full structured transcript is persisted in `DecisionRecord.debate`.
- A debate agent LLM failure degrades that single turn (argument text records the failure) — it never crashes the graph.
- All tests run fully offline with the existing `tests/fakes.py::FakeChatModel` — no network, no API key.
- TDD: failing test first, watch it fail, implement minimally, watch it pass, commit.

---

### Task 1: Debate schemas

**Files:**
- Modify: `src/productagents/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: existing schema module.
- Produces:
  - `DebateArgument(argument: str)` — the LLM output schema for one debate turn.
  - `DebateTurn(round: int, side: str, argument: str)` — one assembled turn.
  - `DecisionRecord` gains `debate: list[DebateTurn]` defaulting to an empty list (existing constructions without `debate` stay valid).

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_schemas.py` (append to the existing file; keep existing tests):

```python
def test_debate_turn_fields():
    from productagents.schemas import DebateTurn

    turn = DebateTurn(round=1, side="advocate", argument="We should build it.")
    assert turn.round == 1
    assert turn.side == "advocate"
    assert turn.argument == "We should build it."


def test_debate_argument_holds_text():
    from productagents.schemas import DebateArgument

    arg = DebateArgument(argument="Risk is too high.")
    assert arg.argument == "Risk is too high."


def test_decision_record_defaults_to_empty_debate():
    from productagents.schemas import (
        DecisionRecord,
        Initiative,
        Recommendation,
    )

    record = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    assert record.debate == []


def test_decision_record_round_trips_with_debate():
    from productagents.schemas import (
        DebateTurn,
        DecisionRecord,
        Initiative,
        Recommendation,
    )

    record = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        debate=[
            DebateTurn(round=1, side="advocate", argument="for"),
            DebateTurn(round=1, side="skeptic", argument="against"),
        ],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    restored = DecisionRecord.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.debate[1].side == "skeptic"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_schemas.py -k "debate" -v`
Expected: FAIL — `ImportError: cannot import name 'DebateTurn'` (and `DebateArgument`).

- [ ] **Step 3: Add the schemas**

In `src/productagents/schemas.py`, add these two classes (place them after `AnalystReport` and before `Recommendation`):

```python
class DebateArgument(BaseModel):
    """Structured output a debate agent (advocate or skeptic) must produce."""

    argument: str = Field(
        description="A single focused argument or rebuttal, two to four sentences."
    )


class DebateTurn(BaseModel):
    """One assembled turn in the debate transcript."""

    round: int
    side: str
    argument: str
```

Then add the `debate` field to `DecisionRecord` (insert the line between `reports` and `timestamp`):

```python
class DecisionRecord(BaseModel):
    """A persisted record of one decision run."""

    initiative: Initiative
    recommendation: Recommendation
    reports: list[AnalystReport]
    debate: list[DebateTurn] = Field(default_factory=list)
    timestamp: str
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: PASS — the four new tests plus all existing schema tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/schemas.py tests/test_schemas.py
git commit -m "feat: add debate schemas and debate transcript field on DecisionRecord"
```

---

### Task 2: Debate agents + debate node

**Files:**
- Create: `src/productagents/agents/debate.py`
- Test: `tests/test_debate.py`

**Interfaces:**
- Consumes: `DebateArgument`, `DebateTurn`, `AnalystReport`, `Initiative` from `productagents.schemas`; `get_writer` from `productagents.agents._stream`.
- Produces:
  - `NODE_ID = "debate"`, `ADVOCATE = "advocate"`, `SKEPTIC = "skeptic"`, `DEFAULT_DEBATE_ROUNDS = 2`.
  - `get_debate_rounds() -> int` — reads `PRODUCTAGENTS_DEBATE_ROUNDS`, default 2, falls back to 2 on invalid / non-positive.
  - `async def debate_node(state: dict, model) -> dict` returning `{"debate": list[DebateTurn]}`. Reads `state["initiative"]` and `state["reports"]`. Emits a `custom` progress event (`{"node": "debate", "status": ...}`) and a `custom` turn event (`{"node": "debate", "turn": turn.model_dump()}`) for each turn. On a per-turn LLM exception, the turn's argument is `"(<side> unavailable: <error>)"` and the loop continues.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_debate.py`:

```python
import pytest

from productagents.agents.debate import debate_node, get_debate_rounds
from productagents.schemas import AnalystReport, DebateArgument, Initiative
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "reports": [
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["demand"],
                signals=["tickets"],
            )
        ],
    }


def test_get_debate_rounds_default(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_DEBATE_ROUNDS", raising=False)
    assert get_debate_rounds() == 2


def test_get_debate_rounds_env_override(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "3")
    assert get_debate_rounds() == 3


def test_get_debate_rounds_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "not-a-number")
    assert get_debate_rounds() == 2
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "0")
    assert get_debate_rounds() == 2


async def test_debate_node_produces_ordered_turns(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    model = FakeChatModel({DebateArgument: DebateArgument(argument="my point")})
    result = await debate_node(_state(), model)
    turns = result["debate"]
    assert [(t.round, t.side) for t in turns] == [
        (1, "advocate"),
        (1, "skeptic"),
        (2, "advocate"),
        (2, "skeptic"),
    ]
    assert all(t.argument == "my point" for t in turns)


async def test_debate_node_degrades_on_failure(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    model = FakeChatModel({DebateArgument: RuntimeError("LLM down")})
    result = await debate_node(_state(), model)
    turns = result["debate"]
    assert len(turns) == 2
    assert "unavailable" in turns[0].argument
    assert turns[0].side == "advocate"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_debate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.agents.debate'`.

- [ ] **Step 3: Implement the debate node**

Create `src/productagents/agents/debate.py`:

```python
"""Structured Advocate-vs-Skeptic debate node.

Runs a configurable number of rounds between an Opportunity Advocate and an
Opportunity Skeptic. Each round the advocate argues first, then the skeptic
rebuts; both see the analyst reports and the debate so far. Each turn is
emitted as a custom stream event for live rendering and collected into a
structured transcript returned in graph state.
"""

import os

from productagents.agents._stream import get_writer
from productagents.schemas import AnalystReport, DebateArgument, DebateTurn, Initiative

NODE_ID = "debate"
ADVOCATE = "advocate"
SKEPTIC = "skeptic"
DEFAULT_DEBATE_ROUNDS = 2

_PERSONA = {
    ADVOCATE: (
        "You are the Opportunity Advocate. You argue that the organization SHOULD "
        "pursue this initiative, emphasizing customer value, business impact, "
        "strategic opportunity, and competitive advantage."
    ),
    SKEPTIC: (
        "You are the Opportunity Skeptic. You argue that the organization should NOT "
        "pursue this initiative, emphasizing opportunity cost, risk, complexity, and "
        "uncertainty."
    ),
}


def get_debate_rounds() -> int:
    """Return the configured number of debate rounds (default 2)."""
    raw = os.environ.get("PRODUCTAGENTS_DEBATE_ROUNDS")
    if raw is None:
        return DEFAULT_DEBATE_ROUNDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_DEBATE_ROUNDS
    return value if value > 0 else DEFAULT_DEBATE_ROUNDS


def _format_reports(reports: list[AnalystReport]) -> str:
    return "\n".join(
        f"- {r.role}: findings={r.findings} signals={r.signals}" for r in reports
    ) or "(no analyst reports)"


def _format_history(turns: list[DebateTurn]) -> str:
    if not turns:
        return "(no prior arguments yet)"
    return "\n".join(f"[round {t.round}] {t.side}: {t.argument}" for t in turns)


def _prompt(
    side: str,
    initiative: Initiative,
    reports: list[AnalystReport],
    history: list[DebateTurn],
) -> str:
    return (
        f"{_PERSONA[side]}\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        f"Analyst findings:\n{_format_reports(reports)}\n\n"
        f"Debate so far:\n{_format_history(history)}\n\n"
        "Make your strongest single argument for your side, directly responding to "
        "the opposing points raised so far."
    )


async def _argue(
    side: str, state: dict, history: list[DebateTurn], model
) -> str:
    structured = model.with_structured_output(DebateArgument)
    result = await structured.ainvoke(
        _prompt(side, state["initiative"], state["reports"], history)
    )
    return result.argument


async def debate_node(state: dict, model) -> dict:
    writer = get_writer()
    rounds = get_debate_rounds()
    turns: list[DebateTurn] = []
    for rnd in range(1, rounds + 1):
        for side in (ADVOCATE, SKEPTIC):
            writer({"node": NODE_ID, "status": f"round {rnd}: {side} arguing…"})
            try:
                argument = await _argue(side, state, turns, model)
            except Exception as exc:  # noqa: BLE001 - degrade one turn, never crash
                argument = f"({side} unavailable: {exc})"
            turn = DebateTurn(round=rnd, side=side, argument=argument)
            turns.append(turn)
            writer({"node": NODE_ID, "turn": turn.model_dump()})
    return {"debate": turns}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_debate.py -v`
Expected: PASS — all five tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/debate.py tests/test_debate.py
git commit -m "feat: add advocate/skeptic debate node with configurable rounds"
```

---

### Task 3: Wire the debate node into the graph

**Files:**
- Modify: `src/productagents/graph.py`
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: `debate_node` from `productagents.agents.debate`; `DebateTurn` from `productagents.schemas`.
- Produces: `GraphState` gains `debate: list[DebateTurn]`. The compiled graph now routes `START → [customer_research, product_analytics] → debate → strategist → END`; the debate node runs once after both analysts (fan-in) and before the strategist.

- [ ] **Step 1: Update the integration test (write the new expectations first)**

Replace the entire body of `tests/test_graph.py` with:

```python
from productagents.graph import build_graph
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    Initiative,
    Recommendation,
)
from tests.fakes import FakeChatModel


def _model():
    return FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["finding"], signals=["signal"]),
            DebateArgument: DebateArgument(argument="my argument"),
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.75,
                rationale="evidence supports it",
                expected_outcomes=["growth"],
            ),
        }
    )


def _initial_state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "evidence": Evidence(
            scenario="sample",
            customer_feedback="demand",
            product_analytics={"x": 1},
        ),
        "reports": [],
        "debate": [],
        "recommendation": None,
    }


async def test_graph_runs_analysts_then_debate_then_strategist(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    graph = build_graph(_model())
    final = await graph.ainvoke(_initial_state())

    assert len(final["reports"]) == 2
    analysts = {r.analyst for r in final["reports"]}
    assert analysts == {"customer_research", "product_analytics"}

    assert [(t.round, t.side) for t in final["debate"]] == [
        (1, "advocate"),
        (1, "skeptic"),
        (2, "advocate"),
        (2, "skeptic"),
    ]

    assert final["recommendation"].recommendation == "Build it"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_graph.py -v`
Expected: FAIL — the graph has no `debate` node yet, so `final["debate"]` is empty (`[] != [(1, "advocate"), …]`).

- [ ] **Step 3: Rewire the graph**

Replace the entire contents of `src/productagents/graph.py` with:

```python
"""LangGraph assembly: parallel analysts → debate → strategist."""

import operator
from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from productagents.agents.customer_research import customer_research_node
from productagents.agents.debate import debate_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.strategist import strategist_node
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Evidence,
    Initiative,
    Recommendation,
)


class GraphState(TypedDict):
    initiative: Initiative
    evidence: Evidence
    reports: Annotated[list[AnalystReport], operator.add]
    debate: list[DebateTurn]
    recommendation: Recommendation | None


def build_graph(model):
    """Compile the decision graph using the injected chat model."""
    graph = StateGraph(GraphState)
    graph.add_node("customer_research", partial(customer_research_node, model=model))
    graph.add_node("product_analytics", partial(product_analytics_node, model=model))
    graph.add_node("debate", partial(debate_node, model=model))
    graph.add_node("strategist", partial(strategist_node, model=model))

    graph.add_edge(START, "customer_research")
    graph.add_edge(START, "product_analytics")
    graph.add_edge("customer_research", "debate")
    graph.add_edge("product_analytics", "debate")
    graph.add_edge("debate", "strategist")
    graph.add_edge("strategist", END)

    return graph.compile()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_graph.py -v`
Expected: PASS — both analysts run, the debate produces four ordered turns, and the strategist produces the recommendation.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `uv run pytest`
Expected: PASS — all tests green (the runner/TUI still pass because the debate node degrades gracefully when their fakes lack `DebateArgument`; those tests are updated in Tasks 5 and 6).

- [ ] **Step 6: Commit**

```bash
git add src/productagents/graph.py tests/test_graph.py
git commit -m "feat: route analysts through the debate node into the strategist"
```

---

### Task 4: Strategist consumes the debate transcript

**Files:**
- Modify: `src/productagents/agents/strategist.py`
- Test: `tests/test_strategist.py`

**Interfaces:**
- Consumes: `state["debate"]` (a `list[DebateTurn]`, read defensively via `state.get("debate", [])`).
- Produces: unchanged signature `async def strategist_node(state: dict, model) -> dict` returning `{"recommendation": Recommendation}`. The prompt now includes the debate transcript.

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_strategist.py` (append; keep existing tests):

```python
async def test_strategist_includes_debate_in_prompt(monkeypatch):
    from productagents.agents import strategist as strategist_module
    from productagents.schemas import DebateTurn

    captured = {}

    def fake_format_debate(turns):
        captured["turns"] = turns
        return "DEBATE-BLOCK"

    monkeypatch.setattr(strategist_module, "_format_debate", fake_format_debate)

    state = _state()
    state["debate"] = [DebateTurn(round=1, side="advocate", argument="for it")]

    from productagents.schemas import Recommendation

    model = FakeChatModel(
        {
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            )
        }
    )
    result = await strategist_node(state, model)
    assert result["recommendation"].recommendation == "Build it"
    assert captured["turns"][0].side == "advocate"
```

> This test relies on the existing `_state()` helper and `strategist_node` / `FakeChatModel` imports already at the top of `tests/test_strategist.py`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_strategist.py::test_strategist_includes_debate_in_prompt -v`
Expected: FAIL — `AttributeError: module 'productagents.agents.strategist' has no attribute '_format_debate'`.

- [ ] **Step 3: Update the strategist**

Replace the entire contents of `src/productagents/agents/strategist.py` with:

```python
"""Product Strategist node: synthesizes analyst reports and the debate."""

from productagents.agents._stream import get_writer
from productagents.schemas import AnalystReport, DebateTurn, Initiative, Recommendation

NODE_ID = "strategist"


def _format_reports(reports: list[AnalystReport]) -> str:
    blocks = []
    for report in reports:
        status = " (FAILED — no input)" if report.failed else ""
        blocks.append(
            f"## {report.role}{status}\n"
            f"Findings: {report.findings}\n"
            f"Signals: {report.signals}\n"
        )
    return "\n".join(blocks)


def _format_debate(turns: list[DebateTurn]) -> str:
    if not turns:
        return "(no debate)"
    return "\n".join(f"[round {t.round}] {t.side}: {t.argument}" for t in turns)


def _prompt(
    initiative: Initiative,
    reports: list[AnalystReport],
    debate: list[DebateTurn],
) -> str:
    return (
        "You are a Product Strategist. Synthesize the analyst reports AND the "
        "advocate/skeptic debate below into a single recommendation. Provide a "
        "recommendation, a confidence score between 0 and 1, a rationale, and "
        "expected outcomes.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        f"Analyst reports:\n{_format_reports(reports)}\n\n"
        f"Debate transcript:\n{_format_debate(debate)}\n"
    )


async def strategist_node(state: dict, model) -> dict:
    writer = get_writer()
    writer({"node": NODE_ID, "status": "synthesizing recommendation…"})
    structured = model.with_structured_output(Recommendation)
    try:
        recommendation = await structured.ainvoke(
            _prompt(
                state["initiative"],
                state["reports"],
                state.get("debate", []),
            )
        )
        writer({"node": NODE_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "status": f"failed: {exc}"})
        recommendation = Recommendation(
            recommendation="Unable to produce a recommendation due to an error.",
            confidence=0.0,
            rationale=f"Strategist failed: {exc}",
            expected_outcomes=[],
        )
    return {"recommendation": recommendation}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_strategist.py -v`
Expected: PASS — the new debate test plus the existing strategist tests (which pass state without a `debate` key and exercise `state.get("debate", []) → []`) all pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/strategist.py tests/test_strategist.py
git commit -m "feat: feed the debate transcript into the strategist prompt"
```

---

### Task 5: Stream debate turns through the runner

**Files:**
- Modify: `src/productagents/runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `DebateTurn` from `productagents.schemas`.
- Produces:
  - New `@dataclass DebateTurnEvent(round: int, side: str, argument: str)`.
  - `FinishedEvent` gains `debate: list[DebateTurn]`.
  - `run_decision` now seeds `"debate": []` in the initial state, maps `custom` chunks containing a `"turn"` key to `DebateTurnEvent`, captures the final `debate` list from the debate node's `updates`, and includes it in the terminal `FinishedEvent`.

- [ ] **Step 1: Update the runner test (write the new expectations first)**

Replace the entire contents of `tests/test_runner.py` with:

```python
from productagents.graph import build_graph
from productagents.runner import (
    DebateTurnEvent,
    FinishedEvent,
    NodeCompleteEvent,
    ProgressEvent,
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


def _graph():
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
        }
    )
    return build_graph(model)


def _inputs():
    return (
        Initiative(title="Add SSO", description="Enterprise SSO"),
        Evidence(scenario="sample", customer_feedback="d", product_analytics={"x": 1}),
    )


async def test_run_decision_emits_all_event_types(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    graph = _graph()
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    progress = [e for e in events if isinstance(e, ProgressEvent)]
    completions = [e for e in events if isinstance(e, NodeCompleteEvent)]
    debate_turns = [e for e in events if isinstance(e, DebateTurnEvent)]
    finished = [e for e in events if isinstance(e, FinishedEvent)]

    assert progress  # at least one in-node progress update
    assert {c.report.analyst for c in completions} == {
        "customer_research",
        "product_analytics",
    }
    assert [(t.round, t.side) for t in debate_turns] == [
        (1, "advocate"),
        (1, "skeptic"),
        (2, "advocate"),
        (2, "skeptic"),
    ]
    assert len(finished) == 1
    assert finished[0].recommendation.recommendation == "Build it"
    assert len(finished[0].reports) == 2
    assert len(finished[0].debate) == 4
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_runner.py -v`
Expected: FAIL — `ImportError: cannot import name 'DebateTurnEvent'`.

- [ ] **Step 3: Update the runner**

Replace the entire contents of `src/productagents/runner.py` with:

```python
"""Normalize LangGraph's streamed chunks into plain UI-facing events."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Evidence,
    Initiative,
    Recommendation,
)


@dataclass
class ProgressEvent:
    node: str
    message: str


@dataclass
class NodeCompleteEvent:
    node: str
    report: AnalystReport


@dataclass
class DebateTurnEvent:
    round: int
    side: str
    argument: str


@dataclass
class FinishedEvent:
    recommendation: Recommendation | None
    reports: list[AnalystReport]
    debate: list[DebateTurn]


async def run_decision(
    graph, initiative: Initiative, evidence: Evidence
) -> AsyncIterator[
    ProgressEvent | NodeCompleteEvent | DebateTurnEvent | FinishedEvent
]:
    """Stream a decision run, yielding normalized events.

    Consumes `graph.astream(..., stream_mode=["updates", "custom"])`. Each item is
    a `(mode, chunk)` tuple. `custom` chunks carry either a debate `turn` dict or a
    progress `status`; `updates` chunks map a node name to the partial state it
    returned.
    """
    initial_state = {
        "initiative": initiative,
        "evidence": evidence,
        "reports": [],
        "debate": [],
        "recommendation": None,
    }
    collected_reports: list[AnalystReport] = []
    collected_debate: list[DebateTurn] = []
    recommendation: Recommendation | None = None

    async for mode, chunk in graph.astream(
        initial_state, stream_mode=["updates", "custom"]
    ):
        if mode == "custom":
            if "turn" in chunk:
                turn = chunk["turn"]
                yield DebateTurnEvent(
                    round=turn["round"],
                    side=turn["side"],
                    argument=turn["argument"],
                )
            else:
                yield ProgressEvent(
                    node=chunk.get("node", ""), message=chunk.get("status", "")
                )
        elif mode == "updates":
            for node_name, node_state in chunk.items():
                if not node_state:
                    continue
                for report in node_state.get("reports", []) or []:
                    collected_reports.append(report)
                    yield NodeCompleteEvent(node=node_name, report=report)
                if node_state.get("debate"):
                    collected_debate = node_state["debate"]
                if node_state.get("recommendation") is not None:
                    recommendation = node_state["recommendation"]

    yield FinishedEvent(
        recommendation=recommendation,
        reports=collected_reports,
        debate=collected_debate,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_runner.py -v`
Expected: PASS — progress, both analyst completions, four ordered debate-turn events, and one finished event carrying the recommendation, two reports, and four debate turns.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/runner.py tests/test_runner.py
git commit -m "feat: stream debate turns and carry the transcript to FinishedEvent"
```

---

### Task 6: Show the debate live in the TUI and record it

**Files:**
- Modify: `src/productagents/tui/app.py`
- Modify: `src/productagents/tui/app.tcss`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `DebateTurnEvent` from `productagents.runner`; `FinishedEvent.debate`.
- Produces: the app gains a scrollable `Static(id="debate")` transcript panel that appends one block per `DebateTurnEvent`. The recorded `DecisionRecord` now includes `debate=event.debate`. Constructor signature `ProductAgentsApp(runner, evidence, *, recorder=record_decision)` is unchanged.

- [ ] **Step 1: Update the TUI test (write the new expectations first)**

Replace the existing `test_app_renders_recommendation_and_records` in `tests/test_tui.py` with the version below (keep the other tests, including `test_main_reports_clear_error_when_model_init_fails`, and keep `import pytest` at the top). Also add `DebateArgument` to the imports from `productagents.schemas` in this file:

```python
async def test_app_renders_recommendation_records_and_shows_debate(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    runner, evidence = _runner_and_evidence()
    recorded = []

    def recorder(record):
        recorded.append(record)

    app = ProductAgentsApp(runner, evidence, recorder=recorder)

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        debate_text = str(pilot.app.query_one("#debate").content)
        strat_text = str(pilot.app.query_one("#strategist").content)
        assert "an argument" in debate_text
        assert "advocate" in debate_text
        assert "Build SSO now" in strat_text

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO now"
    assert len(recorded[0].debate) == 4
    assert recorded[0].debate[0].side == "advocate"
```

And update the `_runner_and_evidence` helper at the top of `tests/test_tui.py` to include the debate fake (replace the existing helper):

```python
def _runner_and_evidence():
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
        }
    )
    graph = build_graph(model)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    return partial(run_decision, graph), evidence
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tui.py::test_app_renders_recommendation_records_and_shows_debate -v`
Expected: FAIL — the app has no `#debate` widget yet (`NoMatches` on `query_one("#debate")`), and/or the imported `DebateArgument` is unused until wiring exists.

- [ ] **Step 3: Update the stylesheet**

Replace the entire contents of `src/productagents/tui/app.tcss` with:

```css
Screen {
    layout: vertical;
}

#initiative-title {
    dock: top;
    margin: 1 1 0 1;
}

#analysts {
    height: auto;
}

.panel {
    border: round $primary;
    padding: 1;
    margin: 1;
    height: auto;
}

#debate-scroll {
    height: 1fr;
    margin: 1;
    border: round $accent;
}

#debate {
    padding: 1;
}

#strategist {
    border: round $success;
    height: auto;
}
```

- [ ] **Step 4: Update the app**

Replace the entire contents of `src/productagents/tui/app.py` with:

```python
"""Textual TUI for running a ProductAgents decision and showing it live."""

import os
import sys
from datetime import datetime, timezone
from functools import partial

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from productagents.evidence import load_scenario
from productagents.graph import build_graph
from productagents.llm import DEFAULT_MODEL, get_model
from productagents.memory import record_decision
from productagents.runner import (
    DebateTurnEvent,
    FinishedEvent,
    NodeCompleteEvent,
    ProgressEvent,
    run_decision,
)
from productagents.schemas import DecisionRecord, Initiative

_PANELS = {
    "customer_research": "Customer Research Analyst",
    "product_analytics": "Product Analytics Analyst",
    "strategist": "Product Strategist",
}


class ProductAgentsApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "ProductAgents"

    def __init__(self, runner, evidence, *, recorder=record_decision):
        super().__init__()
        self._runner = runner
        self._evidence = evidence
        self._recorder = recorder
        self._debate_lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(
            placeholder="Describe the initiative and press Enter…",
            id="initiative-title",
        )
        with Horizontal(id="analysts"):
            yield Static("Waiting…", id="customer_research", classes="panel")
            yield Static("Waiting…", id="product_analytics", classes="panel")
        with VerticalScroll(id="debate-scroll"):
            yield Static("Waiting…", id="debate")
        yield Static("Waiting…", id="strategist", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        for node_id, role in _PANELS.items():
            self.query_one(f"#{node_id}", Static).border_title = role
        self.query_one("#debate-scroll").border_title = "Advocate vs Skeptic Debate"

    def on_input_submitted(self, message: Input.Submitted) -> None:
        title = message.value.strip()
        if not title:
            return
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._debate_lines = []
        self.query_one("#debate", Static).update("…")
        self._run(Initiative(title=title, description=title))

    @work(exclusive=True)
    async def _run(self, initiative: Initiative) -> None:
        recommendation = None
        reports = []
        debate = []
        async for event in self._runner(initiative, self._evidence):
            if isinstance(event, ProgressEvent):
                if event.node in _PANELS:
                    self.query_one(f"#{event.node}", Static).update(
                        f"… {event.message}"
                    )
            elif isinstance(event, NodeCompleteEvent):
                report = event.report
                body = "\n".join(f"• {f}" for f in report.findings) or "(no findings)"
                self.query_one(f"#{event.node}", Static).update(body)
            elif isinstance(event, DebateTurnEvent):
                self._debate_lines.append(
                    f"[{event.side} · round {event.round}] {event.argument}"
                )
                self.query_one("#debate", Static).update(
                    "\n\n".join(self._debate_lines)
                )
            elif isinstance(event, FinishedEvent):
                recommendation = event.recommendation
                reports = event.reports
                debate = event.debate
                self._render_recommendation(recommendation)

        if recommendation is not None:
            self._recorder(
                DecisionRecord(
                    initiative=initiative,
                    recommendation=recommendation,
                    reports=reports,
                    debate=debate,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

    def _render_recommendation(self, recommendation) -> None:
        text = (
            f"[b]{recommendation.recommendation}[/b]\n\n"
            f"Confidence: {recommendation.confidence:.0%}\n\n"
            f"{recommendation.rationale}\n\n"
            "Expected outcomes:\n"
            + "\n".join(f"• {o}" for o in recommendation.expected_outcomes)
        )
        self.query_one("#strategist", Static).update(text)


def _build_app() -> "ProductAgentsApp":
    graph = build_graph(get_model())
    evidence = load_scenario("sample")
    return ProductAgentsApp(partial(run_decision, graph), evidence)


def main() -> None:
    try:
        app = _build_app()
    except Exception as exc:  # noqa: BLE001 - present a clear startup message instead of a traceback
        model = os.environ.get("PRODUCTAGENTS_MODEL", DEFAULT_MODEL)
        print(
            f"Failed to start ProductAgents: {exc}\n"
            f"Check that PRODUCTAGENTS_MODEL ('{model}') is valid and the "
            f"matching provider API key is set (e.g. ANTHROPIC_API_KEY).",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    app.run()
```

- [ ] **Step 5: Run the focused test to verify it passes**

Run: `uv run pytest tests/test_tui.py -v`
Expected: PASS — the debate panel shows the advocate's argument, the strategist panel shows the recommendation, and exactly one `DecisionRecord` with four debate turns is recorded.

> Note: if the installed Textual version differs in how a `Static`'s text is read or how a scroll container exposes `border_title`, adjust the TEST mechanics (how panel text is read) and the widget arrangement to match — but keep the assertions intact: the advocate argument appears in `#debate`, the recommendation appears in `#strategist`, and the recorded `DecisionRecord.debate` has four turns. This mirrors the Textual-version adjustment already made in the slice.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: PASS — every test across the project passes.

- [ ] **Step 7: Commit**

```bash
git add src/productagents/tui/app.py src/productagents/tui/app.tcss tests/test_tui.py
git commit -m "feat: stream the debate live in the TUI and record the transcript"
```

---

### Task 7: Document the debate configuration

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing.
- Produces: documentation only.

- [ ] **Step 1: Document the debate in the run section**

In `README.md`, inside the existing "Running the Slice (first milestone)" section, update the opening paragraph and add a debate note. Replace the paragraph that currently reads:

```markdown
This repository currently implements a thin end-to-end slice: two analysts
(Customer Research + Product Analytics) evaluate a bundled evidence scenario in
parallel and a strategist produces a recommendation, shown live in a TUI.
```

with:

```markdown
This repository currently implements an end-to-end slice: two analysts
(Customer Research + Product Analytics) evaluate a bundled evidence scenario in
parallel, an Opportunity Advocate and an Opportunity Skeptic debate the
initiative over several rounds, and a strategist produces a recommendation —
all shown live in a TUI and saved (with the full debate transcript) to
`decisions.jsonl`.

The number of debate rounds is configurable (each round is one advocate
argument followed by one skeptic rebuttal):

\`\`\`bash
export PRODUCTAGENTS_DEBATE_ROUNDS=2  # default is 2
\`\`\`
```

> Replace the `\`\`\`` markers above with real triple backticks when editing the file.

- [ ] **Step 2: Verify the suite is still green**

Run: `uv run pytest`
Expected: PASS — full suite green (docs change is non-functional).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document the debate layer and PRODUCTAGENTS_DEBATE_ROUNDS"
```

---

## Self-Review

**1. Spec coverage**

- Advocate + Skeptic agents with personas → Task 2. ✓
- Configurable rounds via `PRODUCTAGENTS_DEBATE_ROUNDS` (default 2, advocate-then-skeptic) → Task 2 (`get_debate_rounds`, loop order) + Global Constraints. ✓
- Debate sits between analysts and strategist → Task 3 (graph rewire, fan-in). ✓
- Strategist consumes the transcript → Task 4. ✓
- Live per-turn streaming → Task 2 (custom turn events) + Task 5 (`DebateTurnEvent`) + Task 6 (TUI panel). ✓
- Full transcript persisted in the decision record → Task 1 (`DecisionRecord.debate`) + Task 6 (recorder includes `debate`). ✓
- Graceful per-turn degradation → Task 2 (`except` → "unavailable" argument). ✓
- Offline tests with the fake model → every task uses `FakeChatModel`. ✓
- Docs → Task 7. ✓

**2. Placeholder scan**

No "TBD"/"TODO"/"handle edge cases"/"similar to Task N". Every code step shows complete code. The README backtick caveat is an editing instruction, not a placeholder. ✓

**3. Type consistency**

- `DebateArgument(argument)` is the LLM output everywhere (Tasks 1, 2, 3, 5, 6 fakes); `DebateTurn(round, side, argument)` is the assembled type used in schemas, debate node, graph state, runner, and TUI — consistent. ✓
- Debate custom event shape `{"node": "debate", "turn": turn.model_dump()}` (Task 2) is exactly what the runner unpacks via `chunk["turn"]["round"|"side"|"argument"]` (Task 5). ✓
- `debate_node` returns `{"debate": [...]}` (Task 2); `GraphState.debate` (Task 3) and the runner's `node_state.get("debate")` capture (Task 5) and `FinishedEvent.debate` (Task 5) → `DecisionRecord.debate` (Task 6) all line up. ✓
- `strategist_node` reads `state.get("debate", [])` (Task 4); graph seeds `debate` in state and the slice's existing strategist tests pass state without the key — both paths covered. ✓
- `run_decision` adds `"debate": []` to the initial state matching the new `GraphState` (Task 3/5). ✓
- TUI constructor stays `ProductAgentsApp(runner, evidence, *, recorder=...)` (Task 6) — unchanged from the slice, so `_build_app`/`main` need no change beyond what's shown. ✓

No gaps found.
