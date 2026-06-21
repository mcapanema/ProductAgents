# ProductAgents Risk Evaluation Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Risk Team stage after the strategist — five specialized risk reviewers (Delivery, Adoption, Strategic, Financial, Organizational) assess the recommendation, stream each assessment live into the TUI, and persist all assessments in every decision record.

**Architecture:** A single `risk_node` runs after the strategist (the last stage before END). It runs the five reviewers in a fixed order; each reviewer sees the initiative, the analyst reports, the debate transcript, and the strategist's recommendation, then returns a structured risk level plus rationale. The node emits one custom stream event per reviewer (for live TUI rendering) and returns the structured list of assessments in graph state. The TUI shows each assessment live and records the full list in the `DecisionRecord`. This is Layer 5 ("Risk Evaluation") of the README's seven-stage architecture; nothing consumes the assessments downstream yet (Layer 6 Governance will), so the layer's deliverable is the streamed + persisted assessments.

**Tech Stack:** Python 3.14, UV, LangGraph, LangChain (`init_chat_model`), Pydantic v2, Textual, pytest + pytest-asyncio.

## Global Constraints

- Python `>=3.14`; UV only. Run all commands with `uv run ...` from the repo root.
- All LLM access flows through an injected model; agents never construct a provider client. Risk reviewers produce output via `model.with_structured_output(RiskFinding)`.
- The five reviewers are a fixed, ordered set (not configurable by count): `delivery`, `adoption`, `strategic`, `financial`, `organizational`, run in exactly that order. A run therefore produces exactly five `RiskAssessment`s in that order.
- `reviewer` is exactly one of `"delivery"`, `"adoption"`, `"strategic"`, `"financial"`, `"organizational"`.
- `level` is a free string (the prompt asks for `low` / `medium` / `high`, but the schema does not constrain it — an unexpected value must never raise). This mirrors the existing `DebateTurn.side: str` choice.
- The full list of assessments is persisted in `DecisionRecord.risks`.
- A single reviewer's LLM failure degrades that reviewer only (`level="unknown"`, rationale records the failure, `failed=True`) — it never crashes the graph. This mirrors the existing analyst-node and debate-node degradation pattern.
- All tests run fully offline with the existing `tests/fakes.py::FakeChatModel` — no network, no API key.
- TDD: failing test first, watch it fail, implement minimally, watch it pass, commit.

---

### Task 1: Risk schemas

**Files:**
- Modify: `src/productagents/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: existing schema module.
- Produces:
  - `RiskFinding(level: str, rationale: str)` — the LLM output schema for one reviewer.
  - `RiskAssessment(reviewer: str, role: str, level: str, rationale: str, failed: bool = False)` — one assembled assessment.
  - `DecisionRecord` gains `risks: list[RiskAssessment]` defaulting to an empty list (existing constructions without `risks` stay valid).

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_schemas.py` (append to the existing file; keep existing tests):

```python
def test_risk_finding_holds_level_and_rationale():
    from productagents.schemas import RiskFinding

    finding = RiskFinding(level="high", rationale="tight deadline")
    assert finding.level == "high"
    assert finding.rationale == "tight deadline"


def test_risk_assessment_defaults_not_failed():
    from productagents.schemas import RiskAssessment

    assessment = RiskAssessment(
        reviewer="delivery",
        role="Delivery Risk Reviewer",
        level="medium",
        rationale="some integration work",
    )
    assert assessment.reviewer == "delivery"
    assert assessment.failed is False


def test_decision_record_defaults_to_empty_risks():
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
    assert record.risks == []


def test_decision_record_round_trips_with_risks():
    from productagents.schemas import (
        DecisionRecord,
        Initiative,
        Recommendation,
        RiskAssessment,
    )

    record = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        risks=[
            RiskAssessment(
                reviewer="financial",
                role="Financial Risk Reviewer",
                level="low",
                rationale="cheap to build",
            )
        ],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    restored = DecisionRecord.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.risks[0].reviewer == "financial"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_schemas.py -k "risk" -v`
Expected: FAIL — `ImportError: cannot import name 'RiskFinding'` (and `RiskAssessment`).

- [ ] **Step 3: Add the schemas**

In `src/productagents/schemas.py`, add these two classes immediately after the `DebateTurn` class and before `Recommendation`:

```python
class RiskFinding(BaseModel):
    """Structured output a risk reviewer must produce."""

    level: str = Field(
        description="The assessed risk level: one of 'low', 'medium', or 'high'."
    )
    rationale: str = Field(
        description="A short explanation, two to four sentences, justifying the level."
    )


class RiskAssessment(BaseModel):
    """One assembled risk assessment plus identifying metadata set by the node."""

    reviewer: str
    role: str
    level: str
    rationale: str
    failed: bool = False
```

Then add the `risks` field to `DecisionRecord` (insert the line between `debate` and `timestamp`):

```python
class DecisionRecord(BaseModel):
    """A persisted record of one decision run."""

    initiative: Initiative
    recommendation: Recommendation
    reports: list[AnalystReport]
    debate: list[DebateTurn] = Field(default_factory=list)
    risks: list[RiskAssessment] = Field(default_factory=list)
    timestamp: str
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: PASS — the four new tests plus all existing schema tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/schemas.py tests/test_schemas.py
git commit -m "feat: add risk schemas and risk assessments field on DecisionRecord"
```

---

### Task 2: Risk reviewers + risk node

**Files:**
- Create: `src/productagents/agents/risk.py`
- Test: `tests/test_risk.py`

**Interfaces:**
- Consumes: `RiskFinding`, `RiskAssessment`, `AnalystReport`, `DebateTurn`, `Initiative`, `Recommendation` from `productagents.schemas`; `get_writer` from `productagents.agents._stream`.
- Produces:
  - `NODE_ID = "risk"`.
  - `REVIEWERS: list[tuple[str, str]]` — ordered `(reviewer_id, role)` pairs for the five reviewers.
  - `async def risk_node(state: dict, model) -> dict` returning `{"risks": list[RiskAssessment]}`. Reads `state["initiative"]`, `state["reports"]`, `state["debate"]`, `state["recommendation"]`. Emits a `custom` progress event (`{"node": "risk", "status": ...}`) and a `custom` assessment event (`{"node": "risk", "assessment": assessment.model_dump()}`) for each reviewer. On a per-reviewer LLM exception, the assessment is `RiskAssessment(reviewer=..., role=..., level="unknown", rationale="(<role> unavailable: <error>)", failed=True)` and the loop continues.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_risk.py`:

```python
from productagents.agents.risk import REVIEWERS, risk_node
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Initiative,
    Recommendation,
    RiskFinding,
)
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
        "debate": [DebateTurn(round=1, side="advocate", argument="build it")],
        "recommendation": Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="strong demand",
            expected_outcomes=["growth"],
        ),
    }


def test_reviewers_are_the_five_fixed_roles_in_order():
    assert [r[0] for r in REVIEWERS] == [
        "delivery",
        "adoption",
        "strategic",
        "financial",
        "organizational",
    ]


async def test_risk_node_produces_one_assessment_per_reviewer():
    model = FakeChatModel(
        {RiskFinding: RiskFinding(level="medium", rationale="some risk")}
    )
    result = await risk_node(_state(), model)
    risks = result["risks"]
    assert [r.reviewer for r in risks] == [
        "delivery",
        "adoption",
        "strategic",
        "financial",
        "organizational",
    ]
    assert all(r.level == "medium" for r in risks)
    assert all(r.rationale == "some risk" for r in risks)
    assert all(r.failed is False for r in risks)


async def test_risk_node_degrades_on_failure():
    model = FakeChatModel({RiskFinding: RuntimeError("LLM down")})
    result = await risk_node(_state(), model)
    risks = result["risks"]
    assert len(risks) == 5
    assert all(r.failed for r in risks)
    assert risks[0].level == "unknown"
    assert "unavailable" in risks[0].rationale
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_risk.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.agents.risk'`.

- [ ] **Step 3: Implement the risk node**

Create `src/productagents/agents/risk.py`:

```python
"""Risk Team node: five specialized reviewers assess the recommendation.

Runs after the strategist. Each reviewer (Delivery, Adoption, Strategic,
Financial, Organizational) sees the initiative, the analyst reports, the debate
transcript, and the strategist's recommendation, then returns a structured risk
level plus rationale. Each assessment is emitted as a custom stream event for
live rendering and collected into a structured list returned in graph state.
"""

from productagents.agents._stream import get_writer
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Initiative,
    Recommendation,
    RiskAssessment,
    RiskFinding,
)

NODE_ID = "risk"

# (reviewer_id, role) in fixed evaluation order.
REVIEWERS: list[tuple[str, str]] = [
    ("delivery", "Delivery Risk Reviewer"),
    ("adoption", "Adoption Risk Reviewer"),
    ("strategic", "Strategic Risk Reviewer"),
    ("financial", "Financial Risk Reviewer"),
    ("organizational", "Organizational Risk Reviewer"),
]

_FOCUS = {
    "delivery": "execution feasibility, delivery complexity, and technical risk",
    "adoption": "customer adoption risk and the chance users will not engage",
    "strategic": "alignment with organizational goals and strategic fit",
    "financial": "economic viability, cost, and expected return",
    "organizational": "team capacity and operational constraints",
}


def _format_reports(reports: list[AnalystReport]) -> str:
    return "\n".join(
        f"- {r.role}: findings={r.findings} signals={r.signals}" for r in reports
    ) or "(no analyst reports)"


def _format_debate(turns: list[DebateTurn]) -> str:
    if not turns:
        return "(no debate)"
    return "\n".join(f"[round {t.round}] {t.side}: {t.argument}" for t in turns)


def _prompt(
    reviewer: str,
    role: str,
    initiative: Initiative,
    reports: list[AnalystReport],
    debate: list[DebateTurn],
    recommendation: Recommendation,
) -> str:
    return (
        f"You are a {role}. Evaluate the {_FOCUS[reviewer]} of the recommendation "
        "below. Assign a risk level of low, medium, or high and justify it.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        f"Recommendation: {recommendation.recommendation}\n"
        f"Rationale: {recommendation.rationale}\n"
        f"Expected outcomes: {recommendation.expected_outcomes}\n\n"
        f"Analyst findings:\n{_format_reports(reports)}\n\n"
        f"Debate transcript:\n{_format_debate(debate)}\n"
    )


async def risk_node(state: dict, model) -> dict:
    writer = get_writer()
    structured = model.with_structured_output(RiskFinding)
    assessments: list[RiskAssessment] = []
    for reviewer, role in REVIEWERS:
        writer({"node": NODE_ID, "status": f"{role} assessing…"})
        try:
            finding = await structured.ainvoke(
                _prompt(
                    reviewer,
                    role,
                    state["initiative"],
                    state["reports"],
                    state["debate"],
                    state["recommendation"],
                )
            )
            assessment = RiskAssessment(
                reviewer=reviewer,
                role=role,
                level=finding.level,
                rationale=finding.rationale,
            )
        except Exception as exc:  # noqa: BLE001 - degrade one reviewer, never crash
            assessment = RiskAssessment(
                reviewer=reviewer,
                role=role,
                level="unknown",
                rationale=f"({role} unavailable: {exc})",
                failed=True,
            )
        assessments.append(assessment)
        writer({"node": NODE_ID, "assessment": assessment.model_dump()})
    return {"risks": assessments}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_risk.py -v`
Expected: PASS — all four tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/risk.py tests/test_risk.py
git commit -m "feat: add risk team node with five specialized reviewers"
```

---

### Task 3: Wire the risk node into the graph

**Files:**
- Modify: `src/productagents/graph.py`
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: `risk_node` from `productagents.agents.risk`; `RiskAssessment` from `productagents.schemas`.
- Produces: `GraphState` gains `risks: list[RiskAssessment]`. The compiled graph now routes `START → [customer_research, product_analytics] → debate → strategist → risk → END`; the risk node runs once after the strategist.

- [ ] **Step 1: Update the integration test (write the new expectations first)**

Replace the entire contents of `tests/test_graph.py` with:

```python
from productagents.graph import build_graph
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    Initiative,
    Recommendation,
    RiskFinding,
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
            RiskFinding: RiskFinding(level="medium", rationale="manageable risk"),
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
        "risks": [],
    }


async def test_graph_runs_analysts_debate_strategist_then_risk(monkeypatch):
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

    assert [r.reviewer for r in final["risks"]] == [
        "delivery",
        "adoption",
        "strategic",
        "financial",
        "organizational",
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_graph.py -v`
Expected: FAIL — the graph has no `risk` node yet, so `final["risks"]` is empty (`[] != ["delivery", …]`).

- [ ] **Step 3: Rewire the graph**

Replace the entire contents of `src/productagents/graph.py` with:

```python
"""LangGraph assembly: parallel analysts → debate → strategist → risk."""

import operator
from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from productagents.agents.customer_research import customer_research_node
from productagents.agents.debate import debate_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.risk import risk_node
from productagents.agents.strategist import strategist_node
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Evidence,
    Initiative,
    Recommendation,
    RiskAssessment,
)


class GraphState(TypedDict):
    initiative: Initiative
    evidence: Evidence
    reports: Annotated[list[AnalystReport], operator.add]
    debate: list[DebateTurn]
    recommendation: Recommendation | None
    risks: list[RiskAssessment]


def build_graph(model):
    """Compile the decision graph using the injected chat model."""
    graph = StateGraph(GraphState)
    graph.add_node("customer_research", partial(customer_research_node, model=model))
    graph.add_node("product_analytics", partial(product_analytics_node, model=model))
    graph.add_node("debate", partial(debate_node, model=model))
    graph.add_node("strategist", partial(strategist_node, model=model))
    graph.add_node("risk", partial(risk_node, model=model))

    graph.add_edge(START, "customer_research")
    graph.add_edge(START, "product_analytics")
    graph.add_edge("customer_research", "debate")
    graph.add_edge("product_analytics", "debate")
    graph.add_edge("debate", "strategist")
    graph.add_edge("strategist", "risk")
    graph.add_edge("risk", END)

    return graph.compile()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_graph.py -v`
Expected: PASS — analysts, debate, strategist, then five risk assessments.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `uv run pytest`
Expected: PASS — all tests green (the runner/TUI tests still pass because the risk node degrades gracefully when their fakes lack `RiskFinding`; those tests are updated in Tasks 4 and 5).

- [ ] **Step 6: Commit**

```bash
git add src/productagents/graph.py tests/test_graph.py
git commit -m "feat: route the strategist recommendation through the risk node"
```

---

### Task 4: Stream risk assessments through the runner

**Files:**
- Modify: `src/productagents/runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `RiskAssessment` from `productagents.schemas`.
- Produces:
  - New `@dataclass RiskAssessmentEvent(reviewer: str, role: str, level: str, rationale: str)`.
  - `FinishedEvent` gains `risks: list[RiskAssessment]`.
  - `run_decision` now seeds `"risks": []` in the initial state, maps `custom` chunks containing an `"assessment"` key to `RiskAssessmentEvent`, captures the final `risks` list from the risk node's `updates`, and includes it in the terminal `FinishedEvent`.

- [ ] **Step 1: Update the runner test (write the new expectations first)**

Replace the entire contents of `tests/test_runner.py` with:

```python
from productagents.graph import build_graph
from productagents.runner import (
    DebateTurnEvent,
    FinishedEvent,
    NodeCompleteEvent,
    ProgressEvent,
    RiskAssessmentEvent,
    run_decision,
)
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    Initiative,
    Recommendation,
    RiskFinding,
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
            RiskFinding: RiskFinding(level="low", rationale="cheap"),
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
    risk_events = [e for e in events if isinstance(e, RiskAssessmentEvent)]
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
    assert [r.reviewer for r in risk_events] == [
        "delivery",
        "adoption",
        "strategic",
        "financial",
        "organizational",
    ]
    assert len(finished) == 1
    assert finished[0].recommendation.recommendation == "Build it"
    assert len(finished[0].reports) == 2
    assert len(finished[0].debate) == 4
    assert len(finished[0].risks) == 5
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_runner.py -v`
Expected: FAIL — `ImportError: cannot import name 'RiskAssessmentEvent'`.

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
    RiskAssessment,
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
class RiskAssessmentEvent:
    reviewer: str
    role: str
    level: str
    rationale: str


@dataclass
class FinishedEvent:
    recommendation: Recommendation | None
    reports: list[AnalystReport]
    debate: list[DebateTurn]
    risks: list[RiskAssessment]


async def run_decision(
    graph, initiative: Initiative, evidence: Evidence
) -> AsyncIterator[
    ProgressEvent
    | NodeCompleteEvent
    | DebateTurnEvent
    | RiskAssessmentEvent
    | FinishedEvent
]:
    """Stream a decision run, yielding normalized events.

    Consumes `graph.astream(..., stream_mode=["updates", "custom"])`. Each item is
    a `(mode, chunk)` tuple. `custom` chunks carry a debate `turn` dict, a risk
    `assessment` dict, or a progress `status`; `updates` chunks map a node name to
    the partial state it returned.
    """
    initial_state = {
        "initiative": initiative,
        "evidence": evidence,
        "reports": [],
        "debate": [],
        "recommendation": None,
        "risks": [],
    }
    collected_reports: list[AnalystReport] = []
    collected_debate: list[DebateTurn] = []
    collected_risks: list[RiskAssessment] = []
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
            elif "assessment" in chunk:
                a = chunk["assessment"]
                yield RiskAssessmentEvent(
                    reviewer=a["reviewer"],
                    role=a["role"],
                    level=a["level"],
                    rationale=a["rationale"],
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
                if node_state.get("risks"):
                    collected_risks = node_state["risks"]
                if node_state.get("recommendation") is not None:
                    recommendation = node_state["recommendation"]

    yield FinishedEvent(
        recommendation=recommendation,
        reports=collected_reports,
        debate=collected_debate,
        risks=collected_risks,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_runner.py -v`
Expected: PASS — progress, both analyst completions, four debate-turn events, five risk-assessment events, and one finished event carrying the recommendation, two reports, four debate turns, and five risks.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/runner.py tests/test_runner.py
git commit -m "feat: stream risk assessments and carry them to FinishedEvent"
```

---

### Task 5: Show the risk assessments live in the TUI and record them

**Files:**
- Modify: `src/productagents/tui/app.py`
- Modify: `src/productagents/tui/app.tcss`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `RiskAssessmentEvent` from `productagents.runner`; `FinishedEvent.risks`.
- Produces: the app gains a scrollable `Static(id="risk")` panel (inside `VerticalScroll(id="risk-scroll")`) that appends one block per `RiskAssessmentEvent`. The recorded `DecisionRecord` now includes `risks=event.risks`. Constructor signature `ProductAgentsApp(runner, evidence, *, recorder=record_decision)` is unchanged.

- [ ] **Step 1: Update the TUI test (write the new expectations first)**

Replace the existing `test_app_renders_recommendation_records_and_shows_debate` in `tests/test_tui.py` with the version below (keep the other tests, including `test_main_reports_clear_error_when_model_init_fails`, and keep `import pytest` at the top). Also add `RiskFinding` to the imports from `productagents.schemas` in this file, and add the risk fake to the `_runner_and_evidence` helper.

Replace the imports block:

```python
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    Recommendation,
    RiskFinding,
)
```

Replace the `_runner_and_evidence` helper:

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
            RiskFinding: RiskFinding(level="medium", rationale="some delivery risk"),
        }
    )
    graph = build_graph(model)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    return partial(run_decision, graph), evidence
```

Replace the debate test with this expanded one:

```python
async def test_app_renders_recommendation_records_debate_and_risk(tmp_path, monkeypatch):
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
        risk_text = str(pilot.app.query_one("#risk").content)
        strat_text = str(pilot.app.query_one("#strategist").content)
        assert "an argument" in debate_text
        assert "advocate" in debate_text
        assert "Delivery Risk Reviewer" in risk_text
        assert "medium" in risk_text
        assert "Build SSO now" in strat_text

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO now"
    assert len(recorded[0].debate) == 4
    assert len(recorded[0].risks) == 5
    assert recorded[0].risks[0].reviewer == "delivery"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tui.py::test_app_renders_recommendation_records_debate_and_risk -v`
Expected: FAIL — the app has no `#risk` widget yet (`NoMatches` on `query_one("#risk")`).

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

#risk-scroll {
    height: 1fr;
    margin: 1;
    border: round $warning;
}

#risk {
    padding: 1;
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
    RiskAssessmentEvent,
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
        self._risk_lines: list[str] = []

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
        with VerticalScroll(id="risk-scroll"):
            yield Static("Waiting…", id="risk")
        yield Footer()

    def on_mount(self) -> None:
        for node_id, role in _PANELS.items():
            self.query_one(f"#{node_id}", Static).border_title = role
        self.query_one("#debate-scroll").border_title = "Advocate vs Skeptic Debate"
        self.query_one("#risk-scroll").border_title = "Risk Team"

    def on_input_submitted(self, message: Input.Submitted) -> None:
        title = message.value.strip()
        if not title:
            return
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._debate_lines = []
        self._risk_lines = []
        self.query_one("#debate", Static).update("…")
        self.query_one("#risk", Static).update("…")
        self._run(Initiative(title=title, description=title))

    @work(exclusive=True)
    async def _run(self, initiative: Initiative) -> None:
        recommendation = None
        reports = []
        debate = []
        risks = []
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
            elif isinstance(event, RiskAssessmentEvent):
                self._risk_lines.append(
                    f"[{event.role} · {event.level}] {event.rationale}"
                )
                self.query_one("#risk", Static).update("\n\n".join(self._risk_lines))
            elif isinstance(event, FinishedEvent):
                recommendation = event.recommendation
                reports = event.reports
                debate = event.debate
                risks = event.risks
                self._render_recommendation(recommendation)

        if recommendation is not None:
            self._recorder(
                DecisionRecord(
                    initiative=initiative,
                    recommendation=recommendation,
                    reports=reports,
                    debate=debate,
                    risks=risks,
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
Expected: PASS — the risk panel shows each reviewer's role and level, the debate panel shows the advocate's argument, the strategist panel shows the recommendation, and exactly one `DecisionRecord` with four debate turns and five risk assessments is recorded.

> Note: if the installed Textual version differs in how a `Static`'s text is read or how a scroll container exposes `border_title`, adjust the TEST mechanics (how panel text is read) and the widget arrangement to match — but keep the assertions intact: the reviewer role and level appear in `#risk`, and the recorded `DecisionRecord.risks` has five entries. This mirrors the Textual-version adjustment already made in the debate layer.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: PASS — every test across the project passes.

- [ ] **Step 7: Commit**

```bash
git add src/productagents/tui/app.py src/productagents/tui/app.tcss tests/test_tui.py
git commit -m "feat: stream the risk team live in the TUI and record assessments"
```

---

### Task 6: Document the risk layer

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing.
- Produces: documentation only.

- [ ] **Step 1: Document the risk layer in the run section**

In `README.md`, inside the "Running the Slice (first milestone)" section, replace the opening paragraph that currently reads:

```markdown
This repository currently implements an end-to-end slice: two analysts
(Customer Research + Product Analytics) evaluate a bundled evidence scenario in
parallel, an Opportunity Advocate and an Opportunity Skeptic debate the
initiative over several rounds, and a strategist produces a recommendation —
all shown live in a TUI and saved (with the full debate transcript) to
`decisions.jsonl`.
```

with:

```markdown
This repository currently implements an end-to-end slice: two analysts
(Customer Research + Product Analytics) evaluate a bundled evidence scenario in
parallel, an Opportunity Advocate and an Opportunity Skeptic debate the
initiative over several rounds, a strategist produces a recommendation, and a
Risk Team of five reviewers (Delivery, Adoption, Strategic, Financial,
Organizational) assesses that recommendation — all shown live in a TUI and saved
(with the full debate transcript and risk assessments) to `decisions.jsonl`.
```

- [ ] **Step 2: Verify the suite is still green**

Run: `uv run pytest`
Expected: PASS — full suite green (docs change is non-functional).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document the risk evaluation layer"
```

---

## Self-Review

**1. Spec coverage** (against the README's Risk Team section and Layer 5):

- Five named reviewers — Delivery, Adoption, Strategic, Financial, Organizational → Task 2 (`REVIEWERS`, `_FOCUS`). ✓
- Each reviewer's focus matches the README (execution feasibility / adoption / strategic alignment / economic viability / capacity) → Task 2 (`_FOCUS`). ✓
- Risk stage runs after the recommendation → Task 3 (graph `strategist → risk → END`). ✓
- Reviewers see the recommendation, analyst reports, and debate → Task 2 (`_prompt`). ✓
- Live per-reviewer streaming → Task 2 (custom assessment events) + Task 4 (`RiskAssessmentEvent`) + Task 5 (TUI panel). ✓
- Full assessments persisted in the decision record → Task 1 (`DecisionRecord.risks`) + Task 5 (recorder includes `risks`). ✓
- Graceful per-reviewer degradation → Task 2 (`except` → `failed=True`, `level="unknown"`). ✓
- Offline tests with the fake model → every task uses `FakeChatModel`. ✓
- Docs → Task 6. ✓

**2. Placeholder scan**

No "TBD"/"TODO"/"handle edge cases"/"similar to Task N". Every code step shows complete code. ✓

**3. Type consistency**

- `RiskFinding(level, rationale)` is the LLM output everywhere (Tasks 2, 3, 4, 5 fakes); `RiskAssessment(reviewer, role, level, rationale, failed)` is the assembled type used in schemas, risk node, graph state, runner, and TUI — consistent. ✓
- Risk custom event shape `{"node": "risk", "assessment": assessment.model_dump()}` (Task 2) is exactly what the runner unpacks via `chunk["assessment"]["reviewer"|"role"|"level"|"rationale"]` (Task 4). ✓
- `risk_node` returns `{"risks": [...]}` (Task 2); `GraphState.risks` (Task 3), the runner's `node_state.get("risks")` capture (Task 4), `FinishedEvent.risks` (Task 4) → `DecisionRecord.risks` (Task 5) all line up. ✓
- `RiskAssessmentEvent` carries `reviewer, role, level, rationale` (Task 4); the TUI reads exactly those (Task 5). ✓
- `run_decision` adds `"risks": []` to the initial state matching the new `GraphState` (Task 3/4). ✓
- TUI constructor stays `ProductAgentsApp(runner, evidence, *, recorder=...)` (Task 5) — unchanged, so `_build_app`/`main` need no change beyond what's shown. ✓

No gaps found.
