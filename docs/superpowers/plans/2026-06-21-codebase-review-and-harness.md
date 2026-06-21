# Codebase Review: Dedup Refactors + CLAUDE.md Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the duplication that has accumulated as the slice grew (analyst-node boilerplate, repeated prompt formatters, magic-string enums) and document the directory structure with a per-directory `CLAUDE.md` harness — without changing any runtime behavior.

**Architecture:** Three behavior-preserving refactors land first so the documentation describes the post-refactor code: (1) a shared `run_analyst` helper collapses the five near-identical analyst nodes, (2) a shared `agents/_format.py` ends the copy-pasted prompt formatters, (3) `Literal` types in `schemas.py` replace bare-`str` verdict/level/side enums. Then four new `CLAUDE.md` files (one per key directory) plus an updated root `CLAUDE.md` document the structure and close the doc-drift around the reflection loop.

**Tech Stack:** Python ≥ 3.14, uv, LangGraph, LangChain, Pydantic v2, Textual, pytest (+pytest-asyncio, pytest-cov), ruff, ty.

## Global Constraints

- Requires Python ≥ 3.14; managed with **uv** (not Conda). Run everything via `uv run …`.
- Tests run **fully offline** with `tests/fakes.py::FakeChatModel`; never require an API key.
- `asyncio_mode = "auto"` — `async def test_*` needs no decorator.
- Coverage gate is enforced: `--cov-fail-under=90`. Every task must keep `uv run pytest` green.
- **Nodes degrade, never crash:** every LLM call is wrapped in `try/except Exception` (with `# noqa: BLE001`) returning a fallback. Preserve this in all refactors.
- **Streaming from nodes** uses `agents/_stream.get_writer()`, never `langgraph.config.get_stream_writer()` directly.
- Ruff line-length is 88. The lint rule set is curated in `pyproject.toml`; `TC` (flake8-type-checking) is intentionally excluded — do **not** move Pydantic field-type imports into `if TYPE_CHECKING:` blocks.
- Commit messages end with the two trailers configured for this repo (Co-Authored-By + Claude-Session). Branch off `main`; do not push unless asked.

---

## File Structure

**New source files**
- `src/productagents/agents/_format.py` — shared prompt formatters (`format_reports_brief`, `format_transcript`).
- `src/productagents/agents/_analyst.py` — shared analyst execution helper (`run_analyst`).

**Modified source files**
- `src/productagents/agents/{customer_research,product_analytics,market,business,technical}.py` — each `*_node` becomes a thin delegate to `run_analyst`; keeps its own `_prompt`.
- `src/productagents/agents/{debate,risk,strategist}.py` — drop local report/transcript formatters, import from `_format`.
- `src/productagents/schemas.py` — add `Verdict`, `RiskLevel`, `DebateSide`, `DecidedBy` Literal aliases; apply them.

**New test files**
- `tests/test_format.py` — covers the shared formatters.
- `tests/test_analyst_helper.py` — covers `run_analyst` directly.

**Modified test file**
- `tests/test_schemas.py` — add Literal validation tests.

**New documentation files**
- `src/productagents/CLAUDE.md`, `src/productagents/agents/CLAUDE.md`, `src/productagents/tui/CLAUDE.md`, `tests/CLAUDE.md`.

**Modified documentation**
- `CLAUDE.md` (root) — add annotated directory tree; document the out-of-graph reflection loop.

---

### Task 1: Shared prompt-formatting module

**Files:**
- Create: `src/productagents/agents/_format.py`
- Create test: `tests/test_format.py`
- Modify: `src/productagents/agents/debate.py`, `src/productagents/agents/risk.py`, `src/productagents/agents/strategist.py`

**Interfaces:**
- Produces:
  - `format_reports_brief(reports: list[AnalystReport]) -> str` — one line per analyst (`- {role}: findings=… signals=…`), or `"(no analyst reports)"` when empty.
  - `format_transcript(turns: list[DebateTurn], *, empty: str = "(no debate)") -> str` — one line per turn (`[round {n}] {side}: {argument}`), or `empty` when there are no turns.
- Consumes: `AnalystReport`, `DebateTurn` from `productagents.schemas`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_format.py`:

```python
from productagents.agents._format import format_reports_brief, format_transcript
from productagents.schemas import AnalystReport, DebateTurn


def _report():
    return AnalystReport(
        analyst="customer_research",
        role="Customer Research Analyst",
        findings=["demand"],
        signals=["tickets"],
    )


def test_format_reports_brief_one_line_per_report():
    out = format_reports_brief([_report()])
    assert out == "- Customer Research Analyst: findings=['demand'] signals=['tickets']"


def test_format_reports_brief_empty():
    assert format_reports_brief([]) == "(no analyst reports)"


def test_format_transcript_one_line_per_turn():
    turns = [DebateTurn(round=1, side="advocate", argument="build it")]
    assert format_transcript(turns) == "[round 1] advocate: build it"


def test_format_transcript_custom_empty_label():
    assert format_transcript([], empty="(no prior arguments yet)") == (
        "(no prior arguments yet)"
    )


def test_format_transcript_default_empty_label():
    assert format_transcript([]) == "(no debate)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.agents._format'`

- [ ] **Step 3: Create the module**

Create `src/productagents/agents/_format.py`:

```python
"""Shared formatters that render graph state into prompt text.

Several nodes feed the same structures — the analyst reports and the debate
transcript — into their LLM prompts. These helpers keep that rendering in one
place. `format_reports_brief` is the one-line-per-analyst form used where the
reports are context rather than the subject; the strategist keeps its own
detailed, failure-annotated rendering locally because it is the only consumer.
"""

from productagents.schemas import AnalystReport, DebateTurn


def format_reports_brief(reports: list[AnalystReport]) -> str:
    """One line per analyst (role, findings, signals); used by debate and risk."""
    return (
        "\n".join(
            f"- {r.role}: findings={r.findings} signals={r.signals}" for r in reports
        )
        or "(no analyst reports)"
    )


def format_transcript(turns: list[DebateTurn], *, empty: str = "(no debate)") -> str:
    """Render the debate transcript, one line per turn, or `empty` when there are none."""
    if not turns:
        return empty
    return "\n".join(f"[round {t.round}] {t.side}: {t.argument}" for t in turns)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_format.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Rewire `debate.py` to use the shared formatters**

In `src/productagents/agents/debate.py`, delete the local `_format_reports` and `_format_history` functions (lines 46–58). Add the import near the existing imports:

```python
from productagents.agents._format import format_reports_brief, format_transcript
```

Update `_prompt` to call the shared helpers:

```python
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
        f"Analyst findings:\n{format_reports_brief(reports)}\n\n"
        f"Debate so far:\n{format_transcript(history, empty='(no prior arguments yet)')}\n\n"
        "Make your strongest single argument for your side, directly responding to "
        "the opposing points raised so far."
    )
```

- [ ] **Step 6: Rewire `risk.py` to use the shared formatters**

In `src/productagents/agents/risk.py`, delete the local `_format_reports` and `_format_debate` functions (lines 40–52). Add the import:

```python
from productagents.agents._format import format_reports_brief, format_transcript
```

In `_prompt`, replace `_format_reports(reports)` with `format_reports_brief(reports)` and `_format_debate(debate)` with `format_transcript(debate)`.

- [ ] **Step 7: Rewire `strategist.py` to use the shared transcript formatter**

In `src/productagents/agents/strategist.py`, delete the local `_format_debate` function (lines 21–24). Keep `_format_reports` (the detailed, failure-annotated block — strategist is its only user) and `_format_lessons`. Add the import:

```python
from productagents.agents._format import format_transcript
```

In `_prompt`, replace `_format_debate(debate)` with `format_transcript(debate)`.

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%. The existing `test_debate.py`, `test_risk.py`, `test_strategist.py` still pass unchanged because the rendered prompt text is byte-for-byte identical.

- [ ] **Step 9: Lint**

Run: `uv run ruff check src tests && uv run ruff format --check src tests`
Expected: no errors.

- [ ] **Step 10: Commit**

```bash
git add src/productagents/agents/_format.py tests/test_format.py \
        src/productagents/agents/debate.py src/productagents/agents/risk.py \
        src/productagents/agents/strategist.py
git commit -m "refactor: extract shared prompt formatters into agents/_format"
```

---

### Task 2: Shared analyst-node helper

**Files:**
- Create: `src/productagents/agents/_analyst.py`
- Create test: `tests/test_analyst_helper.py`
- Modify: `src/productagents/agents/customer_research.py`, `product_analytics.py`, `market.py`, `business.py`, `technical.py`

**Interfaces:**
- Produces:
  - `run_analyst(state: dict, model, *, analyst_id: str, role: str, start_status: str, prompt: Callable[[Initiative, Evidence], str]) -> dict` — emits the start/done/failed progress events, issues one `AnalystFindings` structured call, and returns `{"reports": [AnalystReport]}`. On any exception it returns a `failed=True` report with empty findings/signals.
- Consumes: `AnalystFindings`, `AnalystReport`, `Evidence`, `Initiative` from `productagents.schemas`; `get_writer` from `agents._stream`.
- Each `*_node(state, model)` public symbol keeps its exact name and signature, so `graph.py` and existing tests are untouched.

- [ ] **Step 1: Write the failing test**

Create `tests/test_analyst_helper.py`:

```python
from productagents.agents._analyst import run_analyst
from productagents.schemas import AnalystFindings, Evidence, Initiative
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "evidence": Evidence(
            scenario="sample",
            customer_feedback="Enterprises demand SSO.",
            product_analytics={},
        ),
    }


def _prompt(initiative, evidence):
    return f"{initiative.title} :: {evidence.customer_feedback}"


async def test_run_analyst_returns_report():
    model = FakeChatModel(
        {AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"])}
    )
    result = await run_analyst(
        _state(),
        model,
        analyst_id="demo",
        role="Demo Analyst",
        start_status="working…",
        prompt=_prompt,
    )
    report = result["reports"][0]
    assert report.analyst == "demo"
    assert report.role == "Demo Analyst"
    assert report.findings == ["demand"]
    assert report.signals == ["tickets"]
    assert report.failed is False


async def test_run_analyst_degrades_on_failure():
    model = FakeChatModel({AnalystFindings: RuntimeError("LLM down")})
    result = await run_analyst(
        _state(),
        model,
        analyst_id="demo",
        role="Demo Analyst",
        start_status="working…",
        prompt=_prompt,
    )
    report = result["reports"][0]
    assert report.failed is True
    assert report.findings == []
    assert report.signals == []
    assert report.analyst == "demo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_analyst_helper.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.agents._analyst'`

- [ ] **Step 3: Create the helper**

Create `src/productagents/agents/_analyst.py`:

```python
"""Shared execution helper for the five parallel analyst nodes.

Every analyst issues one structured `AnalystFindings` LLM call, wraps it in the
graceful-degradation contract, and emits the same start/done/failed progress
events. They differ only in identity (id/role), the opening status message, and
which `Evidence` fields their prompt renders. `run_analyst` captures the common
shape; each analyst module supplies its own constants and `_prompt` builder.
"""

from collections.abc import Callable

from productagents.agents._stream import get_writer
from productagents.schemas import AnalystFindings, AnalystReport, Evidence, Initiative


async def run_analyst(
    state: dict,
    model,
    *,
    analyst_id: str,
    role: str,
    start_status: str,
    prompt: Callable[[Initiative, Evidence], str],
) -> dict:
    """Run one analyst's structured call, degrading to a failed report on error.

    Returns the `{"reports": [AnalystReport]}` partial state every analyst node
    contributes to the `reports` reducer.
    """
    writer = get_writer()
    writer({"node": analyst_id, "status": start_status})
    structured = model.with_structured_output(AnalystFindings)
    try:
        findings = await structured.ainvoke(
            prompt(state["initiative"], state["evidence"])
        )
        report = AnalystReport(
            analyst=analyst_id,
            role=role,
            findings=findings.findings,
            signals=findings.signals,
        )
        writer({"node": analyst_id, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": analyst_id, "status": f"failed: {exc}"})
        report = AnalystReport(
            analyst=analyst_id, role=role, findings=[], signals=[], failed=True
        )
    return {"reports": [report]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_analyst_helper.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Collapse `customer_research.py`**

Replace the body of `src/productagents/agents/customer_research.py` with:

```python
"""Customer Research Analyst node: reads qualitative customer evidence."""

from productagents.agents._analyst import run_analyst
from productagents.schemas import Evidence, Initiative

ANALYST_ID = "customer_research"
ROLE = "Customer Research Analyst"
_START_STATUS = "reading customer evidence…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the customer feedback below, identify the key customer "
        "pain points and demand signals relevant to this initiative.\n\n"
        f"Customer feedback:\n{evidence.customer_feedback}\n"
    )


async def customer_research_node(state: dict, model) -> dict:
    return await run_analyst(
        state,
        model,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
```

- [ ] **Step 6: Collapse `technical.py`**

Replace the body of `src/productagents/agents/technical.py` with:

```python
"""Technical Analyst node: reads architecture and delivery-complexity evidence."""

from productagents.agents._analyst import run_analyst
from productagents.schemas import Evidence, Initiative

ANALYST_ID = "technical"
ROLE = "Technical Analyst"
_START_STATUS = "assessing technical feasibility…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the technical context below, assess feasibility, technical "
        "risks, and effort and delivery complexity relevant to this initiative.\n\n"
        f"Technical context:\n{evidence.technical_context}\n"
    )


async def technical_node(state: dict, model) -> dict:
    return await run_analyst(
        state,
        model,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
```

- [ ] **Step 7: Collapse `market.py`**

Replace the body of `src/productagents/agents/market.py` with:

```python
"""Market Analyst node: reads competitive and market evidence."""

from productagents.agents._analyst import run_analyst
from productagents.schemas import Evidence, Initiative

ANALYST_ID = "market"
ROLE = "Market Analyst"
_START_STATUS = "scanning the market…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the market intelligence below, identify competitive "
        "intelligence, market opportunities, and strategic context relevant to "
        "this initiative.\n\n"
        f"Market intelligence:\n{evidence.market_intelligence}\n"
    )


async def market_node(state: dict, model) -> dict:
    return await run_analyst(
        state,
        model,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
```

- [ ] **Step 8: Collapse `business.py`**

Replace the body of `src/productagents/agents/business.py` with (note: keeps `import json`):

```python
"""Business Analyst node: reads quantitative business and financial evidence."""

import json

from productagents.agents._analyst import run_analyst
from productagents.schemas import Evidence, Initiative

ANALYST_ID = "business"
ROLE = "Business Analyst"
_START_STATUS = "assessing business impact…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    metrics = json.dumps(evidence.business_metrics, indent=2)
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the business metrics below, assess business impact, goal "
        "alignment, and ROI considerations relevant to this initiative.\n\n"
        f"Business metrics (JSON):\n{metrics}\n"
    )


async def business_node(state: dict, model) -> dict:
    return await run_analyst(
        state,
        model,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
```

- [ ] **Step 9: Collapse `product_analytics.py`**

Replace the body of `src/productagents/agents/product_analytics.py` with (note: keeps `import json`):

```python
"""Product Analytics Analyst node: reads quantitative usage evidence."""

import json

from productagents.agents._analyst import run_analyst
from productagents.schemas import Evidence, Initiative

ANALYST_ID = "product_analytics"
ROLE = "Product Analytics Analyst"
_START_STATUS = "analyzing product metrics…"


def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    analytics = json.dumps(evidence.product_analytics, indent=2)
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        "Using ONLY the product analytics below, identify behavioral insights, "
        "impact estimates, and opportunity sizing relevant to this initiative.\n\n"
        f"Product analytics (JSON):\n{analytics}\n"
    )


async def product_analytics_node(state: dict, model) -> dict:
    return await run_analyst(
        state,
        model,
        analyst_id=ANALYST_ID,
        role=ROLE,
        start_status=_START_STATUS,
        prompt=_prompt,
    )
```

- [ ] **Step 10: Run the full suite**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%. `tests/test_analysts.py` passes unchanged — the node names, returned `AnalystReport` fields, and the rendered prompt text are all identical to before.

- [ ] **Step 11: Lint**

Run: `uv run ruff check src tests && uv run ruff format --check src tests`
Expected: no errors. (If `ruff format` reports diffs, run `uv run ruff format src tests` and re-run the check.)

- [ ] **Step 12: Commit**

```bash
git add src/productagents/agents/_analyst.py tests/test_analyst_helper.py \
        src/productagents/agents/customer_research.py \
        src/productagents/agents/technical.py src/productagents/agents/market.py \
        src/productagents/agents/business.py \
        src/productagents/agents/product_analytics.py
git commit -m "refactor: collapse the five analyst nodes onto a shared run_analyst helper"
```

---

### Task 3: Typed Literal enums in schemas

**Files:**
- Modify: `src/productagents/schemas.py`
- Modify test: `tests/test_schemas.py`

**Interfaces:**
- Produces (module-level type aliases in `schemas.py`):
  - `Verdict = Literal["approve", "reject", "request_analysis"]`
  - `RiskLevel = Literal["low", "medium", "high"]`
  - `DebateSide = Literal["advocate", "skeptic"]`
  - `DecidedBy = Literal["ai", "human"]`
- Applied so that **LLM-output** schemas are strict and **assembled records** that can hold a degraded sentinel are widened by exactly one value:
  - `GovernanceFinding.verdict: Verdict`, `HumanDecision.verdict: Verdict`, `RiskFinding.level: RiskLevel`
  - `DebateTurn.side: DebateSide`
  - `GovernanceVerdict.verdict: Verdict | Literal["error"]`, `GovernanceVerdict.decided_by: DecidedBy`, `GovernanceVerdict.advisory_verdict: Verdict | None`
  - `RiskAssessment.level: RiskLevel | Literal["unknown"]`
- Rationale: the degrade paths construct `GovernanceVerdict(verdict="error", …)` (governance.py:104) and `RiskAssessment(level="unknown", …)` (risk.py:103). Widening those two assembled types by their sentinel keeps the never-crash contract intact while still rejecting genuinely invalid values.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from productagents.schemas import (
    GovernanceFinding,
    GovernanceVerdict,
    RiskAssessment,
    RiskFinding,
)


def test_governance_finding_rejects_unknown_verdict():
    with pytest.raises(ValidationError):
        GovernanceFinding(verdict="maybe", rationale="x")


def test_risk_finding_rejects_unknown_level():
    with pytest.raises(ValidationError):
        RiskFinding(level="catastrophic", rationale="x")


def test_governance_verdict_allows_error_sentinel():
    v = GovernanceVerdict(verdict="error", rationale="down", failed=True)
    assert v.verdict == "error"


def test_governance_verdict_rejects_arbitrary_value():
    with pytest.raises(ValidationError):
        GovernanceVerdict(verdict="nope", rationale="x")


def test_risk_assessment_allows_unknown_sentinel():
    a = RiskAssessment(
        reviewer="delivery",
        role="Delivery Risk Reviewer",
        level="unknown",
        rationale="down",
        failed=True,
    )
    assert a.level == "unknown"
```

> If `tests/test_schemas.py` already imports `pytest` or any of these names at the top, do not duplicate the imports — fold the new names into the existing import block instead.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_schemas.py -k "verdict or level or sentinel" -v`
Expected: FAIL — the `rejects_*` tests fail because the fields are still bare `str` (no `ValidationError` raised).

- [ ] **Step 3: Add the Literal aliases**

In `src/productagents/schemas.py`, change the typing import at the top:

```python
from typing import Literal
```

Add the aliases immediately after the imports (before `class Initiative`):

```python
# Constrained vocabularies shared across the LLM-output schemas, the assembled
# records, and the persisted log. The assembled records widen their field by the
# single degraded sentinel a failing node may emit ("error"/"unknown").
Verdict = Literal["approve", "reject", "request_analysis"]
RiskLevel = Literal["low", "medium", "high"]
DebateSide = Literal["advocate", "skeptic"]
DecidedBy = Literal["ai", "human"]
```

- [ ] **Step 4: Apply the aliases to the schema fields**

In `src/productagents/schemas.py`:

- `DebateTurn.side`: change `side: str` to `side: DebateSide`.
- `RiskFinding.level`: change `level: str = Field(...)` to `level: RiskLevel = Field(...)` (keep the existing `Field(description=…)`).
- `RiskAssessment.level`: change `level: str` to `level: RiskLevel | Literal["unknown"]`.
- `GovernanceFinding.verdict`: change `verdict: str = Field(...)` to `verdict: Verdict = Field(...)` (keep the description).
- `GovernanceVerdict.verdict`: change `verdict: str` to `verdict: Verdict | Literal["error"]`.
- `GovernanceVerdict.decided_by`: change `decided_by: str = "ai"` to `decided_by: DecidedBy = "ai"`.
- `GovernanceVerdict.advisory_verdict`: change `advisory_verdict: str | None = None` to `advisory_verdict: Verdict | None = None`.
- `HumanDecision.verdict`: change `verdict: str = Field(...)` to `verdict: Verdict = Field(...)` (keep the description).

Leave `RiskAssessment.reviewer/role`, `DebateTurn.round/argument`, and all event dataclasses in `runner.py` as-is (those UI DTOs stay decoupled `str`s).

- [ ] **Step 5: Run the new tests**

Run: `uv run pytest tests/test_schemas.py -k "verdict or level or sentinel" -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%. The degrade-path tests (`test_governance.py::test_governance_node_degrades_on_failure` asserting `verdict == "error"`, `test_risk.py::test_risk_node_degrades_on_failure` asserting `level == "unknown"`) still pass because those sentinels are inside the widened types.

- [ ] **Step 7: Type-check and lint**

Run: `uv run ty check src && uv run ruff check src tests`
Expected: no new errors. (`ty==0.0.51` is pinned in the dev group.)

- [ ] **Step 8: Commit**

```bash
git add src/productagents/schemas.py tests/test_schemas.py
git commit -m "refactor: type verdict/level/side enums as Literals in schemas"
```

---

### Task 4: `src/productagents/CLAUDE.md` (package layer map)

**Files:**
- Create: `src/productagents/CLAUDE.md`

**Interfaces:** none (documentation). Describes the post-refactor package.

- [ ] **Step 1: Write the file**

Create `src/productagents/CLAUDE.md`:

```markdown
# src/productagents/ — package map

The implemented slice of the framework. Read top-level `CLAUDE.md` first for the
vision-vs-slice framing and the end-to-end diagram. This file maps the package's
own layers.

## Layers (data flows top to bottom)

| Module | Responsibility |
| --- | --- |
| `schemas.py` | All Pydantic models + the shared `Literal` vocabularies (`Verdict`, `RiskLevel`, `DebateSide`, `DecidedBy`). Two families: **LLM-output** schemas a structured call must return (`AnalystFindings`, `DebateArgument`, `RiskFinding`, `GovernanceFinding`, `Reflection`, `Recommendation`) and **assembled records** nodes build from them (`AnalystReport`, `DebateTurn`, `RiskAssessment`, `GovernanceVerdict`, `OutcomeRecord`, `DecisionRecord`). |
| `evidence.py` | Layer-1 evidence collection behind the `EvidenceSource` protocol. `ScenarioSource` (named bundled scenario) and `DirectorySource` (any folder) both go through `_collect_from_dir`, which records an `EvidenceSourceRef` per loaded field. `collect_evidence(spec)` resolves a user string → source. |
| `llm.py` | The single provider-agnostic `get_model()` factory. **Nodes never call this** — the model is injected into the graph and passed to each node via `partial`. |
| `agents/` | One graph node per file. See `agents/CLAUDE.md`. |
| `graph.py` | Wires nodes into a LangGraph `StateGraph`. Owns `GraphState` (`TypedDict`). `build_graph(model, *, human_in_the_loop=False)` injects the model into every node and optionally appends `human_approval` with an `InMemorySaver` checkpointer. |
| `runner.py` | The boundary between the graph and any UI. `run_decision()` consumes `graph.astream(stream_mode=["updates","custom"])` and yields plain dataclass events (`ProgressEvent`, `NodeCompleteEvent`, `DebateTurnEvent`, `RiskAssessmentEvent`, `GovernanceVerdictEvent`, `FinalVerdictEvent`, `RecallEvent`, `FinishedEvent`). Handles the governance `__interrupt__` by awaiting the `approver` and resuming with `Command(resume=...)`. |
| `memory.py` | Append-only `decisions.jsonl` / `outcomes.jsonl` logs + `select_relevant_lessons()` (lexical retrieval, the read side of Outcome Learning). |
| `tui/` | The Textual app and its modal screens. See `tui/CLAUDE.md`. |
| `data/scenarios/<name>/` | Bundled mock evidence: `customer_feedback.md`, `product_analytics.json`, `market_intelligence.md`, `business_metrics.json`, `technical_context.md`. Only the first two are required; the rest default to empty. |

## Two graph entry points, one model

`graph.py` is the only module that knows LangGraph's shape; `runner.py` is the
only module that knows how to drive it. Everything above `runner` sees just the
event dataclasses. The chat model is created once (`get_model()` in `tui/app.py`)
and threaded down by dependency injection — this is what lets every test inject
`tests/fakes.py::FakeChatModel` instead of a real provider.

## Conventions

- **Nodes degrade, never crash** — every LLM call is wrapped in `try/except
  Exception` (`# noqa: BLE001`) returning a fallback record.
- **Concurrent writes use reducers** — five analysts run in parallel from `START`,
  so `GraphState.reports` is `Annotated[list, operator.add]`.
- **State is seeded at the UI boundary** — `portfolio`/`outcomes` are read from
  the logs in `tui/app.py` and passed into `run_decision`; nodes never touch the
  filesystem (keeps `recall`/`governance` pure and testable).

## Adding a stage

Add the schema(s) → add a node in `agents/` (`get_writer()` + structured output)
→ wire into `graph.py` and `GraphState` → surface a new event in `runner.py` →
render it in `tui/app.py`. Plans live in `docs/superpowers/plans/`.
```

- [ ] **Step 2: Sanity-check the facts**

Run: `uv run python -c "import productagents.schemas as s; assert s.Verdict and s.RiskLevel and s.DebateSide and s.DecidedBy"`
Expected: no error (confirms the aliases referenced in the doc exist after Task 3).

- [ ] **Step 3: Commit**

```bash
git add src/productagents/CLAUDE.md
git commit -m "docs: add package layer map at src/productagents/CLAUDE.md"
```

---

### Task 5: `src/productagents/agents/CLAUDE.md` (node contract)

**Files:**
- Create: `src/productagents/agents/CLAUDE.md`

**Interfaces:** none (documentation). Must describe the post-refactor helpers (`_analyst.run_analyst`, `_format`).

- [ ] **Step 1: Write the file**

Create `src/productagents/agents/CLAUDE.md`:

```markdown
# agents/ — the node layer

One graph node per file. A node is an `async def *_node(state: dict, model) ->
dict` that reads from `state`, optionally issues **one** structured LLM call, and
returns the partial `GraphState` it owns. Nodes are pure functions of their
arguments — the model is injected (never `get_model()` here), and prior decisions
arrive via `state`, never the filesystem.

## The four rules

1. **Degrade, never crash.** Wrap the LLM call in `try/except Exception` with
   `# noqa: BLE001` and return a fallback (`failed=True` report, placeholder
   debate turn, `"error"`/`"unknown"` sentinel, or zero-confidence rec). One
   failure must not abort the graph.
2. **Stream through `get_writer()`.** Import from `agents._stream`, not
   `langgraph.config` — the helper returns a no-op writer when a node is called
   directly in a unit test. Emit `{"node": id, "status": "…"}` for progress and
   richer payloads (`turn`, `assessment`, `verdict`, `final_verdict`) for live
   rendering; `runner.py` translates these into events.
3. **Structured output only.** `model.with_structured_output(Schema)` where
   `Schema` is an LLM-output model from `schemas.py`. Assemble the enriched
   record (with id/role/`failed`) from the result yourself.
4. **Return only your slice of `GraphState`.** e.g. `{"reports": [report]}`,
   `{"debate": turns}`, `{"recommendation": rec}`.

## Files

| File | Node / role |
| --- | --- |
| `_analyst.py` | `run_analyst(...)` — shared executor for the five analysts (progress events + structured call + graceful degradation). Not a node itself. |
| `_format.py` | `format_reports_brief`, `format_transcript` — shared prompt formatters used by debate/risk (and strategist for the transcript). |
| `_stream.py` | `get_writer()` — active stream writer or a no-op outside a graph run. |
| `customer_research.py`, `product_analytics.py`, `market.py`, `business.py`, `technical.py` | The five parallel analysts. Each is a thin delegate: module constants + a `_prompt(initiative, evidence)` + a `*_node` that calls `run_analyst`. |
| `debate.py` | Advocate-vs-Skeptic loop, `get_debate_rounds()` rounds (env `PRODUCTAGENTS_DEBATE_ROUNDS`, default 2). Emits each turn. |
| `recall.py` | Model-free; selects lessons from past decisions via `memory.select_relevant_lessons`. Runs in parallel from `START`. |
| `strategist.py` | Synthesizes reports + debate + recalled lessons into a `Recommendation`. |
| `risk.py` | Five fixed reviewers (`REVIEWERS`), each a structured `RiskFinding`. Emits each assessment. |
| `governance.py` | Portfolio Manager advisory `GovernanceVerdict`, weighed against the recent portfolio window. |
| `human_approval.py` | HITL only. `interrupt()` pauses for a human; the resumed `HumanDecision` becomes the binding verdict (`decided_by="human"`, advisory preserved). |
| `reflection.py` | **Out of graph.** `reflect(decision, note, model)` runs after the fact (triggered from the TUI reflection screen) to produce an `OutcomeRecord` — the capture half of Outcome Learning. |

## Adding an analyst

Copy any analyst file, change `ANALYST_ID` / `ROLE` / `_START_STATUS`, write the
`_prompt`, and let `run_analyst` do the rest. Then register it in `graph.py`
(node + `START`→node and node→`debate` edges) and add a `_PANELS` entry in
`tui/app.py`.

## Testing

Call a node directly with a `FakeChatModel` (`tests/fakes.py`) mapping the
schema class → the instance (or `Exception`) the call should return. No graph,
no event loop boilerplate (`asyncio_mode = "auto"`). See `tests/CLAUDE.md`.
```

- [ ] **Step 2: Sanity-check the facts**

Run: `uv run python -c "from productagents.agents._analyst import run_analyst; from productagents.agents._format import format_reports_brief, format_transcript; from productagents.agents.risk import REVIEWERS; print(len(REVIEWERS))"`
Expected: prints `5` (confirms the symbols the doc names exist).

- [ ] **Step 3: Commit**

```bash
git add src/productagents/agents/CLAUDE.md
git commit -m "docs: document the node contract at agents/CLAUDE.md"
```

---

### Task 6: `src/productagents/tui/CLAUDE.md` (Textual layer)

**Files:**
- Create: `src/productagents/tui/CLAUDE.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Write the file**

Create `src/productagents/tui/CLAUDE.md`:

```markdown
# tui/ — the Textual layer

The only layer that knows about the screen. It consumes the runner's event
dataclasses and knows nothing about LangGraph. `main()` (in `app.py`) is the
`productagents` entry point.

## Files

| File | Role |
| --- | --- |
| `app.py` | `ProductAgentsApp` + `main()`. Builds the model/graph once (`_build_app`), runs a decision in a `@work(exclusive=True)` worker, and updates one panel per event. `app.tcss` is the stylesheet. |
| `approval.py` | `ApprovalScreen` (`ModalScreen[HumanDecision]`). Shows the advisory verdict; the button id (`approve`/`reject`/`request_analysis`) becomes the `HumanDecision.verdict`. |
| `reflection.py` | `ReflectionScreen`. Pick a past decision, describe what happened, and record an `OutcomeRecord` via the injected reflector — drives the out-of-graph reflection loop (bound to `ctrl+r`). |

## The event loop

`app._run` iterates `self._runner(...)` and dispatches by event type:
`ProgressEvent`/`NodeCompleteEvent` → analyst panels (gated by `_PANELS`),
`DebateTurnEvent` → debate scroll, `RiskAssessmentEvent` → risk scroll,
`GovernanceVerdictEvent`/`FinalVerdictEvent` → governance panel, `RecallEvent` →
lessons panel, `FinishedEvent` → render the recommendation and persist a
`DecisionRecord`. Any new event type needs a branch here **and** (usually) a
`_PANELS` entry, or it is silently dropped.

## Dependency-injection seams

`ProductAgentsApp.__init__` takes every external collaborator as a parameter so
the app is testable headless (see `tests/test_tui.py`):

- `runner` — normally `partial(run_decision, graph)`.
- `collector` — `collect_evidence` (resolves the evidence-source input per run).
- `recorder` / `reader` — `record_decision` / `read_decisions` (decision log).
- `outcome_reader` / `outcome_recorder` — `read_outcomes` / `record_outcome`.
- `reflector` — `partial(reflect, model=model)`; `None` disables `ctrl+r`.

`portfolio` and `outcomes` are read from the logs **here** and passed into
`run_decision`, keeping the graph nodes filesystem-free.

## HITL pause

On a governance `__interrupt__`, `run_decision` calls the app's `_ask_human`,
which `push_screen_wait(ApprovalScreen(...))` and returns the `HumanDecision`
that resumes the graph; a `FinalVerdictEvent` then updates the governance panel.

## Testing

Drive the app with Textual's `run_test()` pilot and fakes for every seam; assert
on panel text. The headless tests never start a real model or graph.
```

- [ ] **Step 2: Sanity-check the facts**

Run: `uv run python -c "from productagents.tui.app import ProductAgentsApp, main; from productagents.tui.approval import ApprovalScreen; from productagents.tui.reflection import ReflectionScreen; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add src/productagents/tui/CLAUDE.md
git commit -m "docs: document the Textual layer at tui/CLAUDE.md"
```

---

### Task 7: `tests/CLAUDE.md` (testing conventions)

**Files:**
- Create: `tests/CLAUDE.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Write the file**

Create `tests/CLAUDE.md`:

```markdown
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
- **The TUI:** Textual `run_test()` pilot with fakes injected for every
  `ProductAgentsApp` seam (`tests/test_tui.py`, `test_approval_tui.py`,
  `test_reflection_tui.py`).
- **Pure helpers** (`_format`, `memory.select_relevant_lessons`, `evidence`):
  call directly, no model needed.

## Conventions

- Each test builds its own `state`/fixtures; no shared mutable global state.
- For every node, cover the happy path **and** the degrade path (the failure
  fallback is part of the contract — keep it covered to hold the 90% gate).
- Env-var-driven behavior is tested with `monkeypatch.setenv/​delenv`
  (e.g. `test_debate.py` for `PRODUCTAGENTS_DEBATE_ROUNDS`).
```

- [ ] **Step 2: Verify the suite still describes reality**

Run: `uv run pytest -q`
Expected: PASS, coverage ≥ 90% (confirms the conventions doc matches the running suite).

- [ ] **Step 3: Commit**

```bash
git add tests/CLAUDE.md
git commit -m "docs: document testing conventions at tests/CLAUDE.md"
```

---

### Task 8: Update root `CLAUDE.md` (directory tree + reflection loop)

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none (documentation). Closes the doc-drift: the reflection loop
and the new helper files are currently undocumented at the root.

- [ ] **Step 1: Add an annotated directory tree**

In `CLAUDE.md`, immediately after the end-to-end diagram block (the fenced
`evidence → … → decisions.jsonl` diagram near the top), insert this new section:

```markdown
## Directory structure

```
src/productagents/
├── schemas.py            # all Pydantic models + shared Literal vocabularies
├── evidence.py           # Layer-1 EvidenceSource protocol + scenario/dir sources
├── llm.py                # get_model() — the only provider-agnostic factory
├── graph.py              # LangGraph StateGraph assembly + GraphState
├── runner.py             # graph→UI boundary: normalizes the stream into events
├── memory.py             # decisions.jsonl / outcomes.jsonl + lesson retrieval
├── agents/               # one graph node per file (see agents/CLAUDE.md)
│   ├── _analyst.py       #   shared run_analyst() executor for the 5 analysts
│   ├── _format.py        #   shared prompt formatters
│   ├── _stream.py        #   get_writer() progress-event helper
│   ├── customer_research.py · product_analytics.py · market.py
│   ├── business.py · technical.py            # the five parallel analysts
│   ├── recall.py · strategist.py · risk.py · governance.py
│   ├── human_approval.py # HITL interrupt node (added only when enabled)
│   └── reflection.py     # OUT OF GRAPH: post-hoc outcome reflection
├── tui/                  # Textual app + modal screens (see tui/CLAUDE.md)
│   ├── app.py · app.tcss · approval.py · reflection.py
└── data/scenarios/<name>/  # bundled mock evidence files
tests/                    # offline suite, FakeChatModel (see tests/CLAUDE.md)
```

Each key directory has its own `CLAUDE.md` with the local contract.
```

> Match the surrounding Markdown exactly: the inner tree is a nested fenced block,
> so close the outer section with its own fence as shown.

- [ ] **Step 2: Document the reflection loop**

In `CLAUDE.md`, find the `agents/` bullet in the "Data flow / layers" list. After
the existing `memory.py` bullet (the last one in that list), add:

```markdown
- **Outcome Learning has two halves.** The *injection* half runs inside the graph
  (`recall` → `strategist`). The *capture* half runs **outside** the graph:
  `agents/reflection.py::reflect()` is triggered from the TUI's reflection screen
  (`ctrl+r`, `tui/reflection.py`), compares a past `DecisionRecord`'s predicted
  outcomes against a free-text note, and appends an `OutcomeRecord` to
  `outcomes.jsonl` via `memory.record_outcome`. `recall` later reads those
  outcomes back. The reflection agent is the one agent not wired into `graph.py`.
```

- [ ] **Step 3: Refresh the analyst/formatter mentions**

In `CLAUDE.md`, update the `agents/` bullet in "Data flow / layers" so it reflects
the shared helper. Replace the sentence
"Analysts and the strategist each issue a single structured LLM call;" with:

```markdown
The five analysts share a single executor (`agents/_analyst.py::run_analyst`) and
differ only in their `_prompt`; the strategist issues its own single structured
call. `debate.py` loops rounds, alternating advocate/skeptic personas, each turn
seeing the full transcript so far. Shared prompt formatters live in
`agents/_format.py`.
```

- [ ] **Step 4: Verify Markdown renders and links resolve**

Run: `ls src/productagents/CLAUDE.md src/productagents/agents/CLAUDE.md src/productagents/tui/CLAUDE.md tests/CLAUDE.md`
Expected: all four exist (the per-directory files referenced by the tree).

- [ ] **Step 5: Final full check**

Run: `uv run pytest && uv run ruff check src tests`
Expected: PASS, coverage ≥ 90%, no lint errors.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add directory tree and document the reflection loop in root CLAUDE.md"
```

---

## Self-Review

**Spec coverage:**
- "Review for design/architectural/refactor improvements" → Tasks 1–3 (analyst dedup, formatter dedup, Literal enums), with the findings narrated in this plan's intro.
- "Document the source code's directory structure" → Task 8 Step 1 (annotated tree) + each per-directory `CLAUDE.md`.
- "Create a CLAUDE.md for each key directory" → Tasks 4–7 (`src/productagents/`, `agents/`, `tui/`, `tests/`), the four selected.
- Doc-drift on the reflection loop (found during review) → Task 8 Steps 2–3.

**Placeholder scan:** No `TBD`/"add error handling"/"similar to Task N". Every code step shows complete code; every doc step shows the full file or the exact insertion text.

**Type consistency:** `run_analyst` keyword params (`analyst_id`, `role`, `start_status`, `prompt`) are identical across the helper (Task 2 Step 3) and all five callers (Steps 5–9). The Literal aliases (`Verdict`, `RiskLevel`, `DebateSide`, `DecidedBy`) are defined once (Task 3 Step 3) and applied with the widened sentinels matching the degrade-path assertions in `test_governance.py`/`test_risk.py`. `format_reports_brief`/`format_transcript` signatures match between `_format.py` and every call site.

**Behavior preservation:** Tasks 1–2 produce byte-identical prompt text and identical returned records, so the existing analyst/debate/risk/strategist tests pass unchanged. Task 3 only narrows accepted values (rejecting strings no code produces) while keeping the two sentinels valid.
```
