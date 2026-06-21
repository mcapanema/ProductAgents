# ProductAgents Outcome-Learning Injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Outcome-Learning loop — feed lessons from relevant past decisions into the Product Strategist so new recommendations are informed by what actually happened before.

**Architecture:** A new model-free `recall` node runs in parallel from `START`. It reads the prior decisions (`portfolio`) and prior outcomes (`outcomes`) that the UI boundary seeds into graph state, scores past decisions by lexical similarity to the current initiative, pairs each with its recorded outcome, and writes the matching `lessons_learned` to `state["prior_lessons"]`. The strategist node (now fed by both `debate` and `recall`) injects those lessons into its prompt. This mirrors the existing organizational-memory convention used by the governance node: prior data is read at the UI boundary and arrives via state — nodes never touch the filesystem. The recalled lessons are surfaced as a new runner event, rendered in a new TUI panel, and persisted on the `DecisionRecord` for traceability.

**Tech Stack:** Python 3.14, UV, LangGraph (`StateGraph`), LangChain (`init_chat_model`), Pydantic v2, Textual, pytest + pytest-asyncio.

## Global Constraints

- Python `>=3.14`; UV only. Run all commands with `uv run ...` from the repo root.
- All LLM access flows through an injected model wired in `graph.py` via `partial(node, model=model)`. The strategist already calls `model.with_structured_output(Recommendation)`.
- The `recall` node is intentionally **model-free**: lesson retrieval is deterministic lexical matching, not an LLM call. It is wired with `graph.add_node("recall", recall_node)` (no `partial`/model) and its signature is `async def recall_node(state: dict) -> dict`. This is a deliberate exception to the "every node takes a model" pattern — document it, do not add an unused `model` parameter.
- Streaming from nodes goes through `agents/_stream.get_writer()` (never `langgraph.config.get_stream_writer()` directly).
- Nodes degrade, never crash: the `recall` node wraps its work in `try/except` and returns `{"prior_lessons": []}` on any error.
- **The node never reads the filesystem.** Prior decisions and outcomes are read at the UI boundary (`read_decisions` / `read_outcomes`) and passed into `run_decision`, which seeds them into state. This matches how the governance node consumes `portfolio` today.
- New state keys (`outcomes`, `prior_lessons`), the new `DecisionRecord.prior_lessons` field, and the new `outcome_reader` TUI parameter are all **optional with defaults** so existing constructions and scenarios keep working unchanged.
- All tests run fully offline with `tests/fakes.py::FakeChatModel` and `tmp_path` — no network, no API key. `asyncio_mode = "auto"`, so `async def test_*` functions need no decorator.
- TDD: failing test first, watch it fail, implement minimally, watch it pass, commit.

---

### Task 1: Lesson-retrieval function in `memory.py`

**Files:**
- Modify: `src/productagents/memory.py`
- Test: `tests/test_memory.py`

**Interfaces:**
- Consumes: `Initiative`, `DecisionRecord`, `OutcomeRecord` from `productagents.schemas`.
- Produces:
  - `select_relevant_lessons(initiative: Initiative, decisions: list[DecisionRecord], outcomes: list[OutcomeRecord], *, limit: int = 3) -> list[str]` — pairs each prior decision with its outcome by `decision_id`, scores lexical overlap between the initiative texts, and returns formatted lesson strings from the top `limit` matches. Ignores decisions whose outcome is missing, `failed`, or has no `lessons_learned`. Returns `[]` when nothing is relevant.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_memory.py` (keep existing tests; `DecisionRecord`, `Initiative`, `Recommendation`, `AnalystReport` are already imported at the top):

```python
def _decision(decision_id, title, description="d"):
    from productagents.schemas import DecisionRecord, Initiative, Recommendation

    return DecisionRecord(
        decision_id=decision_id,
        initiative=Initiative(title=title, description=description),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


def _outcome_for(decision_id, lessons, *, accuracy=0.6, failed=False):
    from productagents.schemas import OutcomeRecord

    return OutcomeRecord(
        decision_id=decision_id,
        actual_outcomes=["x"],
        prediction_accuracy=accuracy,
        lessons_learned=lessons,
        reflected_at="2026-06-20T00:00:00+00:00",
        failed=failed,
    )


def test_selects_lessons_from_matching_decision():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [
        _decision("d1", "Add enterprise SSO login"),
        _decision("d2", "Redesign the billing dashboard"),
    ]
    outcomes = [
        _outcome_for("d1", ["SSO took two quarters, not one"], accuracy=0.5),
        _outcome_for("d2", ["billing rewrite slipped"]),
    ]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO support")

    lessons = select_relevant_lessons(initiative, decisions, outcomes)

    assert any("SSO took two quarters" in line for line in lessons)
    assert all("billing rewrite" not in line for line in lessons)
    # provenance: the source initiative title and accuracy are included
    assert any("Add enterprise SSO login" in line for line in lessons)
    assert any("50%" in line for line in lessons)


def test_ignores_decisions_without_an_outcome():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [_decision("d1", "Add enterprise SSO login")]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    assert select_relevant_lessons(initiative, decisions, outcomes=[]) == []


def test_ignores_failed_or_empty_outcomes():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [
        _decision("d1", "Add enterprise SSO login"),
        _decision("d2", "Add SSO provisioning"),
    ]
    outcomes = [
        _outcome_for("d1", ["this lesson is from a failed reflection"], failed=True),
        _outcome_for("d2", []),  # no lessons captured
    ]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    assert select_relevant_lessons(initiative, decisions, outcomes) == []


def test_returns_empty_when_no_token_overlap():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [_decision("d1", "Migrate the data warehouse")]
    outcomes = [_outcome_for("d1", ["warehouse migration was risky"])]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    assert select_relevant_lessons(initiative, decisions, outcomes) == []


def test_respects_limit():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [_decision(f"d{i}", "Add SSO login support") for i in range(5)]
    outcomes = [_outcome_for(f"d{i}", [f"lesson {i}"]) for i in range(5)]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    lessons = select_relevant_lessons(initiative, decisions, outcomes, limit=2)
    assert len(lessons) == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_memory.py -k "select or matching or ignores or overlap or limit" -v`
Expected: FAIL — `ImportError: cannot import name 'select_relevant_lessons' from 'productagents.memory'`.

- [ ] **Step 3: Implement the retrieval function**

In `src/productagents/memory.py`, add `import re` at the top (below the existing `from pathlib import Path`), and extend the schema import to include `Initiative`:

```python
import re
from pathlib import Path

from productagents.schemas import DecisionRecord, Initiative, OutcomeRecord
```

Then add this block at the end of `memory.py`:

```python
# Short, ubiquitous words carry no signal for matching past initiatives.
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with",
        "is", "are", "be", "this", "that", "it", "as", "by", "at", "from",
        "our", "we", "add", "new", "support",
    }
)


def _tokens(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) > 2 and word not in _STOPWORDS
    }


def select_relevant_lessons(
    initiative: Initiative,
    decisions: list[DecisionRecord],
    outcomes: list[OutcomeRecord],
    *,
    limit: int = 3,
) -> list[str]:
    """Return formatted lessons from the past decisions most similar to `initiative`.

    Pairs each prior decision with its recorded outcome (by `decision_id`), scores
    lexical overlap between the initiative texts, and returns the lessons of the
    top `limit` matches. Decisions whose outcome is missing, failed, or has no
    captured lessons are ignored. Returns [] when nothing relevant is found.
    """
    by_id = {
        outcome.decision_id: outcome
        for outcome in outcomes
        if not outcome.failed and outcome.lessons_learned
    }
    query = _tokens(f"{initiative.title} {initiative.description}")
    if not query:
        return []

    scored: list[tuple[int, DecisionRecord, OutcomeRecord]] = []
    for decision in decisions:
        outcome = by_id.get(decision.decision_id)
        if outcome is None:
            continue
        past = _tokens(
            f"{decision.initiative.title} {decision.initiative.description}"
        )
        overlap = len(query & past)
        if overlap == 0:
            continue
        scored.append((overlap, decision, outcome))

    scored.sort(key=lambda item: item[0], reverse=True)

    lessons: list[str] = []
    for _, decision, outcome in scored[:limit]:
        for lesson in outcome.lessons_learned:
            lessons.append(
                f'From "{decision.initiative.title}" '
                f"(prediction accuracy {outcome.prediction_accuracy:.0%}): {lesson}"
            )
    return lessons
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: PASS — the five new tests plus all existing memory tests.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/memory.py tests/test_memory.py
git commit -m "feat: add lexical lesson-retrieval over past decisions"
```

---

### Task 2: The `recall` node

**Files:**
- Create: `src/productagents/agents/recall.py`
- Test: `tests/test_recall.py`

**Interfaces:**
- Consumes: `select_relevant_lessons` (Task 1); `get_writer` from `productagents.agents._stream`; `state["initiative"]`, `state.get("portfolio", [])`, `state.get("outcomes", [])`.
- Produces:
  - `NODE_ID = "recall"`.
  - `async def recall_node(state: dict) -> dict` returning `{"prior_lessons": list[str]}`, degrading to `{"prior_lessons": []}` on error. **No `model` parameter** (see Global Constraints).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_recall.py`:

```python
from productagents.agents.recall import recall_node
from productagents.schemas import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)


def _state_with_history():
    decision = DecisionRecord(
        decision_id="d1",
        initiative=Initiative(title="Add enterprise SSO login", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    outcome = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["shipped late"],
        prediction_accuracy=0.5,
        lessons_learned=["SSO integrations take longer than predicted"],
        reflected_at="2026-06-20T00:00:00+00:00",
    )
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "portfolio": [decision],
        "outcomes": [outcome],
    }


async def test_recall_surfaces_relevant_lessons():
    result = await recall_node(_state_with_history())
    lessons = result["prior_lessons"]
    assert any("take longer than predicted" in line for line in lessons)


async def test_recall_empty_without_history():
    state = {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "portfolio": [],
        "outcomes": [],
    }
    result = await recall_node(state)
    assert result["prior_lessons"] == []


async def test_recall_tolerates_missing_state_keys():
    # No portfolio/outcomes keys at all — must default, not KeyError.
    state = {"initiative": Initiative(title="Add SSO", description="Enterprise SSO")}
    result = await recall_node(state)
    assert result["prior_lessons"] == []


async def test_recall_degrades_on_error(monkeypatch):
    from productagents.agents import recall as recall_module

    def boom(*_args, **_kwargs):
        raise RuntimeError("retrieval blew up")

    monkeypatch.setattr(recall_module, "select_relevant_lessons", boom)
    result = await recall_node(_state_with_history())
    assert result["prior_lessons"] == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_recall.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.agents.recall'`.

- [ ] **Step 3: Implement the node**

Create `src/productagents/agents/recall.py`:

```python
"""Recall node: surface lessons from relevant past decisions.

This is the injection half of Outcome Learning. It runs in parallel from START,
reads the prior decisions and outcomes seeded into state at the UI boundary,
selects the lessons from the most similar past initiatives, and writes them to
`prior_lessons` for the strategist to consume. It is model-free (retrieval is
deterministic lexical matching) and degrades to an empty list on any error.
"""

from productagents.agents._stream import get_writer
from productagents.memory import select_relevant_lessons

NODE_ID = "recall"


async def recall_node(state: dict) -> dict:
    writer = get_writer()
    writer({"node": NODE_ID, "status": "recalling lessons from past decisions…"})
    try:
        lessons = select_relevant_lessons(
            state["initiative"],
            state.get("portfolio", []),
            state.get("outcomes", []),
        )
        writer({"node": NODE_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "status": f"failed: {exc}"})
        lessons = []
    return {"prior_lessons": lessons}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_recall.py -v`
Expected: PASS — all four recall tests.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/recall.py tests/test_recall.py
git commit -m "feat: add recall node that selects lessons from past decisions"
```

---

### Task 3: Inject lessons into the strategist prompt

**Files:**
- Modify: `src/productagents/agents/strategist.py`
- Test: `tests/test_strategist.py`

**Interfaces:**
- Consumes: `state.get("prior_lessons", [])` (produced by the recall node, Task 2).
- Produces: a `_format_lessons(lessons: list[str]) -> str` helper and a `prior_lessons` parameter on `_prompt`; `strategist_node` passes `state.get("prior_lessons", [])`. The return shape (`{"recommendation": Recommendation}`) is unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_strategist.py` (keep existing tests; `strategist_node`, `Initiative`, `Recommendation`, `AnalystReport`, `FakeChatModel`, and the `_state` helper are already present):

```python
async def test_strategist_includes_prior_lessons_in_prompt(monkeypatch):
    from productagents.agents import strategist as strategist_module

    captured = {}

    def fake_format_lessons(lessons):
        captured["lessons"] = lessons
        return "LESSONS-BLOCK"

    monkeypatch.setattr(strategist_module, "_format_lessons", fake_format_lessons)

    state = _state()
    state["prior_lessons"] = ['From "Add SSO login": SSO took two quarters']

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
    assert captured["lessons"] == ['From "Add SSO login": SSO took two quarters']
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_strategist.py -k prior_lessons -v`
Expected: FAIL — `AttributeError: <module 'productagents.agents.strategist'> does not have the attribute '_format_lessons'`.

- [ ] **Step 3: Add the lessons formatter and wire it into the prompt**

In `src/productagents/agents/strategist.py`, add the `_format_lessons` helper immediately after `_format_debate`:

```python
def _format_lessons(lessons: list[str]) -> str:
    if not lessons:
        return "(no relevant past lessons)"
    return "\n".join(f"- {lesson}" for lesson in lessons)
```

Replace the `_prompt` function signature and body with one that also takes and renders `prior_lessons`:

```python
def _prompt(
    initiative: Initiative,
    reports: list[AnalystReport],
    debate: list[DebateTurn],
    prior_lessons: list[str],
) -> str:
    return (
        "You are a Product Strategist. Synthesize the analyst reports AND the "
        "advocate/skeptic debate below into a single recommendation. Provide a "
        "recommendation, a confidence score between 0 and 1, a rationale, and "
        "expected outcomes. Apply the lessons from past decisions where they are "
        "relevant.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        f"Analyst reports:\n{_format_reports(reports)}\n\n"
        f"Debate transcript:\n{_format_debate(debate)}\n\n"
        f"Lessons from past decisions:\n{_format_lessons(prior_lessons)}\n"
    )
```

In `strategist_node`, update the `_prompt(...)` call to pass the lessons:

```python
        recommendation = await structured.ainvoke(
            _prompt(
                state["initiative"],
                state["reports"],
                state.get("debate", []),
                state.get("prior_lessons", []),
            )
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_strategist.py -v`
Expected: PASS — the new test plus all existing strategist tests (the debate-injection test still passes because `prior_lessons` defaults to `[]`).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/strategist.py tests/test_strategist.py
git commit -m "feat: inject past-decision lessons into the strategist prompt"
```

---

### Task 4: Wire the `recall` node into the graph

**Files:**
- Modify: `src/productagents/graph.py`
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: `recall_node` (Task 2).
- Produces: `GraphState` gains `outcomes: list[OutcomeRecord]` and `prior_lessons: list[str]`. The compiled graph runs `recall` from `START`; `strategist` now fans in from both `debate` and `recall`. No existing edge is removed.

- [ ] **Step 1: Update the graph test (RED)**

In `tests/test_graph.py`, extend `_initial_state()` to include the two new keys (add them inside the returned dict, after `"portfolio": []`):

```python
        "portfolio": [],
        "outcomes": [],
        "prior_lessons": [],
        "governance": None,
```

Then, at the end of `test_graph_runs_through_governance`, add an assertion that the recall node populated state:

```python
    assert final["governance"].verdict == "approve"

    assert final["prior_lessons"] == []
```

(With an empty portfolio/outcomes the recall node returns `[]`; this proves the node ran and wrote the key.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_graph.py -v`
Expected: FAIL — `KeyError: 'prior_lessons'` (the graph has no node writing that key yet).

- [ ] **Step 3: Wire the node and extend `GraphState`**

In `src/productagents/graph.py`, add the recall import next to the other analyst/agent imports:

```python
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.recall import recall_node
from productagents.agents.risk import risk_node
```

Extend the schema import to include `OutcomeRecord`:

```python
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    DecisionRecord,
    Evidence,
    GovernanceVerdict,
    Initiative,
    OutcomeRecord,
    Recommendation,
    RiskAssessment,
)
```

Add the two new keys to `GraphState` (after `portfolio`):

```python
    portfolio: list[DecisionRecord]
    outcomes: list[OutcomeRecord]
    prior_lessons: list[str]
    governance: GovernanceVerdict | None
```

In `build_graph`, register the recall node (it takes no model — do **not** wrap it in `partial`). Add it immediately after the `technical` node registration:

```python
    graph.add_node("technical", partial(technical_node, model=model))
    graph.add_node("recall", recall_node)
```

Add the recall edges next to the analyst edges: a `START → recall` edge, and a `recall → strategist` edge (so the strategist waits for both the debate and the recall):

```python
    graph.add_edge(START, "technical")
    graph.add_edge(START, "recall")
    graph.add_edge("customer_research", "debate")
    graph.add_edge("product_analytics", "debate")
    graph.add_edge("market", "debate")
    graph.add_edge("business", "debate")
    graph.add_edge("technical", "debate")
    graph.add_edge("debate", "strategist")
    graph.add_edge("recall", "strategist")
    graph.add_edge("strategist", "risk")
```

(Leave the existing `risk → governance → END` edges unchanged.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_graph.py -v`
Expected: PASS — `final["prior_lessons"] == []` and all prior assertions still hold (`strategist` runs once, after both `debate` and `recall`).

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest`
Expected: PASS — the strategist already reads `prior_lessons` with a default (Task 3), and the runner seeds the key (it does not yet, but `recall_node` uses `.get`, so the graph test passes; runner wiring lands in Task 5).

- [ ] **Step 6: Commit**

```bash
git add src/productagents/graph.py tests/test_graph.py
git commit -m "feat: run the recall node and feed lessons into the strategist"
```

---

### Task 5: Surface lessons through the runner and persist them

**Files:**
- Modify: `src/productagents/runner.py`
- Modify: `src/productagents/schemas.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: the `prior_lessons` key written by the recall node (Task 2/4).
- Produces:
  - `RecallEvent(lessons: list[str])` dataclass, added to the `run_decision` return union.
  - `run_decision` gains `outcomes: list[OutcomeRecord] | None = None`; it seeds `state["outcomes"]` and `state["prior_lessons"]`, yields a `RecallEvent` when the recall node reports, and includes `prior_lessons` on the `FinishedEvent`.
  - `FinishedEvent` gains `prior_lessons: list[str]`.
  - `DecisionRecord` gains `prior_lessons: list[str] = Field(default_factory=list)`.

- [ ] **Step 1: Write the failing test**

In `tests/test_runner.py`, add `OutcomeRecord` and `DecisionRecord` to the schema imports and `RecallEvent` to the runner imports:

```python
from productagents.runner import (
    DebateTurnEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    NodeCompleteEvent,
    ProgressEvent,
    RecallEvent,
    RiskAssessmentEvent,
    run_decision,
)
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    DecisionRecord,
    Evidence,
    GovernanceFinding,
    Initiative,
    OutcomeRecord,
    Recommendation,
    RiskFinding,
)
```

Append this test to `tests/test_runner.py`:

```python
async def test_run_decision_recalls_and_emits_lessons(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    graph = _graph()
    initiative, evidence = _inputs()

    prior = DecisionRecord(
        decision_id="d1",
        initiative=Initiative(title="Add enterprise SSO login", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    outcome = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["shipped late"],
        prediction_accuracy=0.5,
        lessons_learned=["SSO integrations take longer than predicted"],
        reflected_at="2026-06-20T00:00:00+00:00",
    )

    events = [
        e
        async for e in run_decision(
            graph, initiative, evidence, portfolio=[prior], outcomes=[outcome]
        )
    ]

    recalls = [e for e in events if isinstance(e, RecallEvent)]
    finished = [e for e in events if isinstance(e, FinishedEvent)]

    assert len(recalls) == 1
    assert any("take longer than predicted" in line for line in recalls[0].lessons)
    assert any(
        "take longer than predicted" in line for line in finished[0].prior_lessons
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_runner.py -k recalls_and_emits -v`
Expected: FAIL — `ImportError: cannot import name 'RecallEvent' from 'productagents.runner'`.

- [ ] **Step 3: Add the `DecisionRecord.prior_lessons` field**

In `src/productagents/schemas.py`, in the `DecisionRecord` class, add the field after `governance` (before `timestamp`):

```python
    governance: GovernanceVerdict | None = None
    prior_lessons: list[str] = Field(default_factory=list)
    timestamp: str
```

- [ ] **Step 4: Add `RecallEvent`, the `outcomes` parameter, and `FinishedEvent.prior_lessons`**

In `src/productagents/runner.py`:

Add `OutcomeRecord` to the schema imports:

```python
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    DecisionRecord,
    Evidence,
    GovernanceVerdict,
    Initiative,
    OutcomeRecord,
    Recommendation,
    RiskAssessment,
)
```

Add the `RecallEvent` dataclass immediately above `FinishedEvent`:

```python
@dataclass
class RecallEvent:
    lessons: list[str]
```

Add `prior_lessons` to `FinishedEvent`:

```python
@dataclass
class FinishedEvent:
    recommendation: Recommendation | None
    reports: list[AnalystReport]
    debate: list[DebateTurn]
    risks: list[RiskAssessment]
    governance: GovernanceVerdict | None
    prior_lessons: list[str]
```

Update the `run_decision` signature and return-union to include `outcomes` and `RecallEvent`:

```python
async def run_decision(
    graph,
    initiative: Initiative,
    evidence: Evidence,
    portfolio: list[DecisionRecord] | None = None,
    outcomes: list[OutcomeRecord] | None = None,
) -> AsyncIterator[
    ProgressEvent
    | NodeCompleteEvent
    | DebateTurnEvent
    | RiskAssessmentEvent
    | GovernanceVerdictEvent
    | RecallEvent
    | FinishedEvent
]:
```

Seed the two new keys in `initial_state` (after `"portfolio"`):

```python
        "portfolio": portfolio or [],
        "outcomes": outcomes or [],
        "prior_lessons": [],
        "governance": None,
    }
```

Add a `collected_lessons` accumulator next to the other collectors:

```python
    collected_risks: list[RiskAssessment] = []
    collected_lessons: list[str] = []
    recommendation: Recommendation | None = None
```

In the `updates` branch, surface `prior_lessons` (add this inside the `for node_name, node_state in chunk.items():` loop, after the `risks` handling):

```python
                if node_state.get("risks"):
                    collected_risks = node_state["risks"]
                if "prior_lessons" in node_state:
                    collected_lessons = node_state["prior_lessons"]
                    yield RecallEvent(lessons=collected_lessons)
```

Finally, pass `prior_lessons` to the terminal `FinishedEvent`:

```python
    yield FinishedEvent(
        recommendation=recommendation,
        reports=collected_reports,
        debate=collected_debate,
        risks=collected_risks,
        governance=governance,
        prior_lessons=collected_lessons,
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_runner.py -v`
Expected: PASS — the new recall test plus `test_run_decision_emits_all_event_types` (which constructs no `outcomes`, so the recall node yields a `RecallEvent` with an empty `lessons` list and `FinishedEvent.prior_lessons == []`).

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: PASS — `DecisionRecord.prior_lessons` is optional, so memory round-trip tests and the TUI recorder are unaffected.

- [ ] **Step 7: Commit**

```bash
git add src/productagents/runner.py src/productagents/schemas.py tests/test_runner.py
git commit -m "feat: emit recalled lessons as a runner event and persist them"
```

---

### Task 6: Show recalled lessons in the TUI and feed outcomes in

**Files:**
- Modify: `src/productagents/tui/app.py`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `read_outcomes` from `productagents.memory`; `RecallEvent` from `productagents.runner`; `FinishedEvent.prior_lessons`.
- Produces:
  - `ProductAgentsApp` gains an `outcome_reader=read_outcomes` constructor parameter.
  - A `#recall` panel ("Lessons from Past Decisions") registered in `_PANELS` and yielded in `compose` (before `#strategist`).
  - `_run` reads outcomes, passes `outcomes=` to the runner, renders `RecallEvent` into `#recall`, and persists `prior_lessons` on the `DecisionRecord`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tui.py` (keep existing tests; `partial`, `pytest`, `run_decision`, the schema imports, `ProductAgentsApp`, `FakeChatModel`, and `_runner_and_evidence` are already present). This test seeds a relevant prior decision + outcome so the recall panel renders a real lesson:

```python
async def test_app_renders_recalled_lessons(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.schemas import (
        DecisionRecord,
        Initiative,
        OutcomeRecord,
        Recommendation,
    )

    runner, evidence = _runner_and_evidence()

    prior = DecisionRecord(
        decision_id="d1",
        initiative=Initiative(title="Add enterprise SSO login", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    outcome = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["shipped late"],
        prediction_accuracy=0.5,
        lessons_learned=["SSO integrations take longer than predicted"],
        reflected_at="2026-06-20T00:00:00+00:00",
    )

    recorded = []
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=recorded.append,
        reader=lambda: [prior],
        outcome_reader=lambda: [outcome],
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        recall_text = str(pilot.app.query_one("#recall").content)

    assert "take longer than predicted" in recall_text
    assert len(recorded) == 1
    assert any(
        "take longer than predicted" in line for line in recorded[0].prior_lessons
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tui.py -k recalled_lessons -v`
Expected: FAIL — `TypeError: ProductAgentsApp.__init__() got an unexpected keyword argument 'outcome_reader'` (or `NoMatches` on `#recall`).

- [ ] **Step 3: Import `read_outcomes` and `RecallEvent`; register the panel**

In `src/productagents/tui/app.py`, extend the memory import to include `read_outcomes`:

```python
from productagents.memory import (
    read_decisions,
    read_outcomes,
    record_decision,
    record_outcome,
)
```

Add `RecallEvent` to the runner imports:

```python
from productagents.runner import (
    DebateTurnEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    NodeCompleteEvent,
    ProgressEvent,
    RecallEvent,
    RiskAssessmentEvent,
    run_decision,
)
```

Add the recall panel to `_PANELS` (after the five analysts, before `strategist`):

```python
_PANELS = {
    "customer_research": "Customer Research Analyst",
    "product_analytics": "Product Analytics Analyst",
    "market": "Market Analyst",
    "business": "Business Analyst",
    "technical": "Technical Analyst",
    "recall": "Lessons from Past Decisions",
    "strategist": "Product Strategist",
}
```

- [ ] **Step 4: Add the constructor parameter and the panel widget**

In `ProductAgentsApp.__init__`, add the `outcome_reader` parameter and store it (place it next to `reader`):

```python
    def __init__(
        self,
        runner,
        evidence,
        *,
        recorder=record_decision,
        reader=read_decisions,
        outcome_reader=read_outcomes,
        reflector=None,
        outcome_recorder=record_outcome,
    ):
        super().__init__()
        self._runner = runner
        self._evidence = evidence
        self._recorder = recorder
        self._reader = reader
        self._outcome_reader = outcome_reader
        self._reflector = reflector
        self._outcome_recorder = outcome_recorder
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []
```

In `compose`, yield the recall panel immediately before the `#strategist` panel:

```python
        with VerticalScroll(id="debate-scroll"):
            yield Static("Waiting…", id="debate")
        yield Static("Waiting…", id="recall", classes="panel")
        yield Static("Waiting…", id="strategist", classes="panel")
```

(No `app.tcss` change is required: `#recall` reuses the existing `.panel` class. It is already reset and titled automatically because it is in `_PANELS`.)

- [ ] **Step 5: Read outcomes, render the event, and persist the lessons**

In the `_run` worker, capture lessons and pass outcomes to the runner. Replace the opening of `_run` (down through the `async for` header) with:

```python
    @work(exclusive=True)
    async def _run(self, initiative: Initiative) -> None:
        recommendation = None
        reports = []
        debate = []
        risks = []
        governance = None
        prior_lessons: list[str] = []
        portfolio = self._reader()
        outcomes = self._outcome_reader()
        async for event in self._runner(
            initiative, self._evidence, portfolio=portfolio, outcomes=outcomes
        ):
```

Add a `RecallEvent` branch to the event loop (place it just before the `FinishedEvent` branch):

```python
            elif isinstance(event, RecallEvent):
                body = "\n".join(f"• {line}" for line in event.lessons) or (
                    "(no relevant past lessons)"
                )
                self.query_one("#recall", Static).update(body)
            elif isinstance(event, FinishedEvent):
                recommendation = event.recommendation
                reports = event.reports
                debate = event.debate
                risks = event.risks
                governance = event.governance
                prior_lessons = event.prior_lessons
                self._render_recommendation(recommendation)
```

Persist `prior_lessons` on the recorded `DecisionRecord`:

```python
        if recommendation is not None:
            self._recorder(
                DecisionRecord(
                    initiative=initiative,
                    recommendation=recommendation,
                    reports=reports,
                    debate=debate,
                    risks=risks,
                    governance=governance,
                    prior_lessons=prior_lessons,
                    timestamp=datetime.now(UTC).isoformat(),
                )
            )
```

- [ ] **Step 6: Keep the existing TUI tests hermetic**

The existing `test_app_renders_recommendation_records_debate_and_risk` and `test_app_renders_new_analyst_panels` construct `ProductAgentsApp` without an `outcome_reader`, so they would fall back to the real `read_outcomes` (which reads `outcomes.jsonl` from the cwd). Pass an explicit empty reader to both so they stay isolated. In each of those two tests, change the `ProductAgentsApp(...)` construction to add `outcome_reader=lambda: []`:

```python
    app = ProductAgentsApp(
        runner, evidence, recorder=recorder, reader=lambda: [], outcome_reader=lambda: []
    )
```

and

```python
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
    )
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_tui.py -v`
Expected: PASS — the new recalled-lessons test plus the two updated existing tests and the error-path test.

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest`
Expected: PASS — full suite green.

- [ ] **Step 9: Commit**

```bash
git add src/productagents/tui/app.py tests/test_tui.py
git commit -m "feat: render recalled lessons in the TUI and record them on the decision"
```

---

### Task 7: Document the closed Outcome-Learning loop

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing.
- Produces: documentation only.

- [ ] **Step 1: Update the slice diagram in `CLAUDE.md`**

In `CLAUDE.md`, in the "What this is" section, replace the slice diagram line:

```
evidence → [customer_research ∥ product_analytics ∥ market ∥ business ∥ technical] → debate (advocate vs skeptic) → strategist → risk → governance → decisions.jsonl
```

with one that shows the recall node feeding the strategist:

```
evidence → [customer_research ∥ product_analytics ∥ market ∥ business ∥ technical] → debate (advocate vs skeptic) ┐
                                                                  recall (past lessons) ┴→ strategist → risk → governance → decisions.jsonl
```

- [ ] **Step 2: Document the injection half in `CLAUDE.md`**

In `CLAUDE.md`, find the `memory.py` bullet in the "Data flow / layers" list and replace it with:

```
- `memory.py` — append-only `decisions.jsonl` and `outcomes.jsonl` logs (the "organizational memory"). `select_relevant_lessons()` scores past decisions by lexical similarity to the current initiative and returns the lessons of the closest matches — this is the read side of Outcome Learning.
```

Then, in the "Architecture" section, add this sentence to the end of the paragraph that begins "`GraphState` is a `TypedDict`":

```
The model-free `recall` node runs in parallel from `START`, selects lessons from relevant past decisions (read at the UI boundary and seeded into state, like `portfolio`), and fans into `strategist` alongside `debate`, closing the Outcome-Learning loop.
```

- [ ] **Step 3: Mark Outcome Learning as fully implemented in `README.md`**

In `README.md`, locate the Outcome Learning description. If it is marked as partial / capture-only, update it to state that the loop is closed: reflections recorded as `OutcomeRecord`s in `outcomes.jsonl` are now retrieved by lexical relevance and injected into the strategist's prompt on future decisions. (Edit only the Outcome-Learning prose; do not restructure other sections.)

- [ ] **Step 4: Verify the suite is still green**

Run: `uv run pytest`
Expected: PASS — docs changes are non-functional.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: close the Outcome-Learning loop (lesson injection)"
```

---

## Self-Review

**1. Spec coverage** (against the chosen iteration — Outcome-Learning injection half):

- Retrieve relevant past decisions + their lessons → Task 1 `select_relevant_lessons` (lexical scoring, pairs decisions↔outcomes by `decision_id`, filters failed/empty). ✓
- A graph stage that performs the recall → Task 2 `recall` node + Task 4 wiring (`START → recall → strategist`). ✓
- Inject lessons into the strategist → Task 3 (`_format_lessons` + `prior_lessons` prompt section). ✓
- Lessons read at the UI boundary, not from the node (matches the governance/`portfolio` convention) → Task 5 (`run_decision(outcomes=...)` seeds state) + Task 6 (`outcome_reader`). ✓
- Loop is visible to the user → Task 5 `RecallEvent` + Task 6 `#recall` panel. ✓
- Loop is traceable / persisted → `DecisionRecord.prior_lessons` (Task 5 schema) recorded by the TUI (Task 6). ✓
- Graceful degradation → recall node `try/except → []` (Task 2); `select_relevant_lessons` returns `[]` on no match. ✓
- Backward compatibility → new state keys, schema field, and TUI param all optional/defaulted; `recall_node` uses `.get`; strategist uses `.get("prior_lessons", [])` (Tasks 2–6). ✓
- Offline tests → every task uses `FakeChatModel`/`tmp_path`/seeded readers; no network. ✓
- Docs → Task 7. ✓

**2. Placeholder scan**

No "TBD"/"TODO"/"handle edge cases"/"similar to Task N". Every code step shows complete code. The only prose-only edit is Task 7 Step 3 (README), which is documentation by nature and bounded to the Outcome-Learning section. ✓

**3. Type consistency**

- `select_relevant_lessons(initiative, decisions, outcomes, *, limit=3) -> list[str]` — identical signature in Task 1 (definition), Task 2 (call, positional args + default limit), and the Task 1 tests. ✓
- `recall_node(state: dict) -> dict` returning `{"prior_lessons": list[str]}` — consistent across Task 2 (node), Task 4 (`add_node("recall", recall_node)`, no model), Task 5 (runner reads `node_state["prior_lessons"]`), and the graph/runner tests. ✓
- `NODE_ID = "recall"` matches the graph `add_node`/`add_edge` names (Task 4) and the `_PANELS` key + `#recall` widget id (Task 6). ✓
- State keys `outcomes` and `prior_lessons` match across `GraphState` (Task 4), `run_decision` seeding (Task 5), `recall_node` (Task 2), and the strategist's `state.get("prior_lessons", [])` (Task 3). ✓
- `RecallEvent(lessons: list[str])` — defined in Task 5, imported and rendered in Task 6, asserted in the Task 5/6 tests. ✓
- `FinishedEvent.prior_lessons` and `DecisionRecord.prior_lessons` (both `list[str]`) — defined in Task 5, consumed in Task 6. ✓
- `outcome_reader` defaults to `read_outcomes` — defined in Task 6 constructor, supplied in the Task 6 tests, and passed as `outcomes=` to `run_decision` (whose `outcomes` param is defined in Task 5). ✓

No gaps found.
