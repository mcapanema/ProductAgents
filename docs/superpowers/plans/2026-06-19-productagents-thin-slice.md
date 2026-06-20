# ProductAgents Thin Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working end-to-end ProductAgents slice where a user enters a product initiative, two analysts (Customer Research + Product Analytics) evaluate mock evidence in parallel via a LangGraph graph, a strategist produces a typed recommendation, and the whole run streams live into a Textual TUI and is logged to `decisions.jsonl`.

**Architecture:** A LangGraph `StateGraph` fans out to two analyst nodes and fans into a strategist node. All LLM access goes through a provider-agnostic factory (`init_chat_model`) and every agent emits strongly-typed Pydantic output via `with_structured_output`. A normalized async runner consumes `graph.astream(...)` and yields plain event objects; the Textual TUI consumes those events in a worker and renders live panels. Agents take an injected model so the whole pipeline is testable offline with a fake chat model.

**Tech Stack:** Python 3.14, UV, LangGraph, LangChain (`init_chat_model`), Pydantic v2, Textual, pytest + pytest-asyncio.

## Global Constraints

- Python `>=3.14`; dependency/venv management via **UV only** (no Conda).
- All LLM access flows through `productagents.llm.get_model()` — agents never construct a provider client directly.
- Model selection is config-driven: env `PRODUCTAGENTS_MODEL` (default `anthropic:claude-sonnet-4-6`), optional `PRODUCTAGENTS_MODEL_PROVIDER`.
- Every agent output is a Pydantic v2 model produced via `model.with_structured_output(...)`.
- `Recommendation.confidence` is a float in `[0.0, 1.0]`.
- Agents accept an injected model parameter so tests run offline with a fake model — no network in any test.
- Evidence is loaded from bundled scenario files under `src/productagents/data/scenarios/<name>/`.
- TDD: write the failing test first, watch it fail, implement minimally, watch it pass, commit.
- Run all commands with `uv run ...` from the repo root.

---

### Task 1: Project scaffolding (UV + package skeleton + pytest)

**Files:**
- Create: `pyproject.toml`
- Create: `src/productagents/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `.python-version`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an importable `productagents` package (exposing `productagents.__version__: str`), a working `uv run pytest`, and an `uv`-managed virtual environment with all runtime + dev dependencies installed.

- [ ] **Step 1: Write the failing smoke test**

Create `tests/__init__.py` as an empty file, and `tests/test_smoke.py`:

```python
def test_package_imports():
    import productagents

    assert productagents.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents'` (or uv reports no project yet).

- [ ] **Step 3: Create the project files**

Create `.python-version`:

```text
3.14
```

Create `pyproject.toml`:

```toml
[project]
name = "productagents"
version = "0.1.0"
description = "Multi-agent framework for product decision-making under uncertainty."
requires-python = ">=3.14"
dependencies = [
    "langgraph>=0.6",
    "langchain>=1.0",
    "langchain-anthropic>=0.3",
    "textual>=4.0",
    "pydantic>=2.7",
]

[project.scripts]
productagents = "productagents.tui.app:main"

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/productagents"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Create `src/productagents/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Sync the environment**

Run: `uv sync`
Expected: uv creates `.venv`, resolves and installs langgraph, langchain, langchain-anthropic, textual, pydantic, pytest, pytest-asyncio, and writes `uv.lock`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS — `test_package_imports PASSED`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock .python-version src/productagents/__init__.py tests/__init__.py tests/test_smoke.py
git commit -m "feat: scaffold productagents package with uv and pytest"
```

---

### Task 2: Typed schemas

**Files:**
- Create: `src/productagents/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: nothing.
- Produces (all Pydantic v2 `BaseModel`s):
  - `Initiative(title: str, description: str)`
  - `Evidence(scenario: str, customer_feedback: str, product_analytics: dict)`
  - `AnalystFindings(findings: list[str], signals: list[str])` — the LLM output schema for an analyst.
  - `AnalystReport(analyst: str, role: str, findings: list[str], signals: list[str], failed: bool = False)`
  - `Recommendation(recommendation: str, confidence: float, rationale: str, expected_outcomes: list[str])` with `confidence` constrained to `[0.0, 1.0]`.
  - `DecisionRecord(initiative: Initiative, recommendation: Recommendation, reports: list[AnalystReport], timestamp: str)`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from productagents.schemas import (
    AnalystFindings,
    AnalystReport,
    DecisionRecord,
    Evidence,
    Initiative,
    Recommendation,
)


def test_initiative_fields():
    init = Initiative(title="Add SSO", description="Enterprise single sign-on")
    assert init.title == "Add SSO"
    assert init.description == "Enterprise single sign-on"


def test_analyst_report_defaults_not_failed():
    report = AnalystReport(
        analyst="customer_research",
        role="Customer Research Analyst",
        findings=["users want SSO"],
        signals=["12 enterprise tickets"],
    )
    assert report.failed is False


def test_recommendation_confidence_must_be_in_range():
    with pytest.raises(ValidationError):
        Recommendation(
            recommendation="Build it",
            confidence=1.5,
            rationale="because",
            expected_outcomes=["higher retention"],
        )


def test_decision_record_round_trips_through_json():
    record = DecisionRecord(
        initiative=Initiative(title="Add SSO", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.8,
            rationale="strong demand",
            expected_outcomes=["enterprise unblock"],
        ),
        reports=[
            AnalystReport(
                analyst="product_analytics",
                role="Product Analytics Analyst",
                findings=["login drop-off"],
                signals=["30% churn at auth"],
            )
        ],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    dumped = record.model_dump_json()
    restored = DecisionRecord.model_validate_json(dumped)
    assert restored == record


def test_analyst_findings_holds_lists():
    findings = AnalystFindings(findings=["a"], signals=["b"])
    assert findings.findings == ["a"]
    assert findings.signals == ["b"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.schemas'`.

- [ ] **Step 3: Implement the schemas**

Create `src/productagents/schemas.py`:

```python
"""Strongly-typed schemas shared across agents, graph state, and persistence."""

from pydantic import BaseModel, Field


class Initiative(BaseModel):
    """A product proposal under evaluation."""

    title: str
    description: str


class Evidence(BaseModel):
    """Mock evidence loaded from a named scenario."""

    scenario: str
    customer_feedback: str
    product_analytics: dict


class AnalystFindings(BaseModel):
    """Structured output an analyst LLM call must produce."""

    findings: list[str] = Field(
        description="Key conclusions drawn from the evidence."
    )
    signals: list[str] = Field(
        description="Specific supporting data points or quotes from the evidence."
    )


class AnalystReport(BaseModel):
    """An analyst's findings plus identifying metadata set by the node."""

    analyst: str
    role: str
    findings: list[str]
    signals: list[str]
    failed: bool = False


class Recommendation(BaseModel):
    """The strategist's decision proposal."""

    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    expected_outcomes: list[str]


class DecisionRecord(BaseModel):
    """A persisted record of one decision run."""

    initiative: Initiative
    recommendation: Recommendation
    reports: list[AnalystReport]
    timestamp: str
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: PASS — all five tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/schemas.py tests/test_schemas.py
git commit -m "feat: add typed schemas for initiatives, evidence, reports, and decisions"
```

---

### Task 3: Evidence loader + bundled sample scenario

**Files:**
- Create: `src/productagents/evidence.py`
- Create: `src/productagents/data/scenarios/sample/customer_feedback.md`
- Create: `src/productagents/data/scenarios/sample/product_analytics.json`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `Evidence` from `productagents.schemas`.
- Produces:
  - `class EvidenceError(Exception)` — raised on missing/malformed scenario.
  - `SCENARIOS_DIR: pathlib.Path` — the bundled scenarios directory.
  - `load_scenario(name: str, base_dir: Path | None = None) -> Evidence`
  - `list_scenarios(base_dir: Path | None = None) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_evidence.py`:

```python
import json

import pytest

from productagents.evidence import EvidenceError, list_scenarios, load_scenario


def test_loads_bundled_sample_scenario():
    evidence = load_scenario("sample")
    assert evidence.scenario == "sample"
    assert isinstance(evidence.customer_feedback, str)
    assert evidence.customer_feedback.strip() != ""
    assert isinstance(evidence.product_analytics, dict)


def test_sample_listed_in_scenarios():
    assert "sample" in list_scenarios()


def test_missing_scenario_raises(tmp_path):
    with pytest.raises(EvidenceError):
        load_scenario("does-not-exist", base_dir=tmp_path)


def test_malformed_analytics_raises(tmp_path):
    scenario = tmp_path / "broken"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("ok")
    (scenario / "product_analytics.json").write_text("{not valid json")
    with pytest.raises(EvidenceError):
        load_scenario("broken", base_dir=tmp_path)


def test_loads_from_custom_base_dir(tmp_path):
    scenario = tmp_path / "custom"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("feedback text")
    (scenario / "product_analytics.json").write_text(json.dumps({"dau": 100}))
    evidence = load_scenario("custom", base_dir=tmp_path)
    assert evidence.customer_feedback == "feedback text"
    assert evidence.product_analytics == {"dau": 100}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_evidence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.evidence'`.

- [ ] **Step 3: Create the bundled sample scenario**

Create `src/productagents/data/scenarios/sample/customer_feedback.md`:

```markdown
# Customer Feedback — Authentication & Access

## Enterprise interviews
- "We can't roll this out company-wide without SSO. Security won't approve shared passwords." — VP Eng, 400-seat prospect
- "Onboarding new teammates takes too long because every person sets up their own login." — IT admin, existing customer
- "We already use Okta for everything else; not supporting it is a dealbreaker." — Procurement lead

## Support tickets (last 90 days)
- 18 tickets requesting SAML / SSO support, 12 from accounts above $50k ARR.
- 9 tickets about password reset friction during team onboarding.

## NPS verbatims
- Detractor: "Login management is painful for larger teams."
- Passive: "Product is great but access control feels built for small teams."
```

Create `src/productagents/data/scenarios/sample/product_analytics.json`:

```json
{
  "initiative_area": "authentication",
  "monthly_active_users": 21500,
  "enterprise_accounts": 47,
  "auth_funnel": {
    "invite_sent": 12000,
    "account_created": 7300,
    "first_login_completed": 5100
  },
  "onboarding_drop_off_rate": 0.30,
  "enterprise_arr_share": 0.62,
  "support_tickets_auth_related_90d": 27
}
```

- [ ] **Step 4: Implement the evidence loader**

Create `src/productagents/evidence.py`:

```python
"""Load mock evidence for a named scenario from bundled data files."""

import json
from pathlib import Path

from productagents.schemas import Evidence

SCENARIOS_DIR = Path(__file__).parent / "data" / "scenarios"

_FEEDBACK_FILE = "customer_feedback.md"
_ANALYTICS_FILE = "product_analytics.json"


class EvidenceError(Exception):
    """Raised when a scenario is missing or its files are malformed."""


def _base(base_dir: Path | None) -> Path:
    return base_dir if base_dir is not None else SCENARIOS_DIR


def list_scenarios(base_dir: Path | None = None) -> list[str]:
    root = _base(base_dir)
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def load_scenario(name: str, base_dir: Path | None = None) -> Evidence:
    scenario_dir = _base(base_dir) / name
    if not scenario_dir.is_dir():
        raise EvidenceError(f"Scenario not found: {name!r} (looked in {scenario_dir})")

    feedback_path = scenario_dir / _FEEDBACK_FILE
    analytics_path = scenario_dir / _ANALYTICS_FILE

    if not feedback_path.is_file():
        raise EvidenceError(f"Missing {_FEEDBACK_FILE} in scenario {name!r}")
    if not analytics_path.is_file():
        raise EvidenceError(f"Missing {_ANALYTICS_FILE} in scenario {name!r}")

    customer_feedback = feedback_path.read_text(encoding="utf-8")
    try:
        product_analytics = json.loads(analytics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(
            f"Malformed {_ANALYTICS_FILE} in scenario {name!r}: {exc}"
        ) from exc

    if not isinstance(product_analytics, dict):
        raise EvidenceError(
            f"{_ANALYTICS_FILE} in scenario {name!r} must be a JSON object"
        )

    return Evidence(
        scenario=name,
        customer_feedback=customer_feedback,
        product_analytics=product_analytics,
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_evidence.py -v`
Expected: PASS — all five tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/productagents/evidence.py src/productagents/data tests/test_evidence.py
git commit -m "feat: add evidence loader and bundled sample scenario"
```

---

### Task 4: Provider-agnostic model factory + fake model test helper

**Files:**
- Create: `src/productagents/llm.py`
- Create: `tests/fakes.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (only `init_chat_model`).
- Produces:
  - `DEFAULT_MODEL: str = "anthropic:claude-sonnet-4-6"`
  - `get_model()` — reads `PRODUCTAGENTS_MODEL` / `PRODUCTAGENTS_MODEL_PROVIDER` and returns a chat model via `init_chat_model`.
  - Test helper `tests/fakes.py`: `FakeChatModel(results: dict[type, object])` whose `.with_structured_output(schema)` returns an object whose `.ainvoke(_)` returns `results[schema]` (or raises it if it is an `Exception`). Used by every later test to run agents offline.

- [ ] **Step 1: Write the failing tests**

Create `tests/fakes.py`:

```python
"""Test doubles for offline agent/graph testing."""


class _FakeStructured:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, _input):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakeChatModel:
    """Stands in for a LangChain chat model in tests.

    `results` maps a Pydantic schema class to the instance that
    `with_structured_output(schema).ainvoke(...)` should return. If the mapped
    value is an Exception instance, `ainvoke` raises it instead.
    """

    def __init__(self, results: dict):
        self._results = results

    def with_structured_output(self, schema, **_kwargs):
        if schema not in self._results:
            raise KeyError(f"FakeChatModel has no result for schema {schema!r}")
        return _FakeStructured(self._results[schema])
```

Create `tests/test_llm.py`:

```python
import productagents.llm as llm


def test_default_model_used_when_env_unset(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.delenv("PRODUCTAGENTS_MODEL", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    result = llm.get_model()

    assert result == "MODEL"
    assert captured["model"] == llm.DEFAULT_MODEL
    assert captured["kwargs"] == {}


def test_env_overrides_model_and_provider(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.setenv("PRODUCTAGENTS_MODEL", "gpt-5.5")
    monkeypatch.setenv("PRODUCTAGENTS_MODEL_PROVIDER", "openai")
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["model"] == "gpt-5.5"
    assert captured["kwargs"] == {"model_provider": "openai"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.llm'`.

- [ ] **Step 3: Implement the model factory**

Create `src/productagents/llm.py`:

```python
"""Provider-agnostic chat-model factory.

Every agent obtains its model through `get_model()` so the provider can be
swapped via configuration without touching agent code.
"""

import os

from langchain.chat_models import init_chat_model

DEFAULT_MODEL = "anthropic:claude-sonnet-4-6"


def get_model():
    """Return a chat model selected by environment configuration.

    `PRODUCTAGENTS_MODEL` sets the model (default `DEFAULT_MODEL`). When given,
    `PRODUCTAGENTS_MODEL_PROVIDER` is passed through as `model_provider`.
    """
    model = os.environ.get("PRODUCTAGENTS_MODEL", DEFAULT_MODEL)
    provider = os.environ.get("PRODUCTAGENTS_MODEL_PROVIDER")
    if provider:
        return init_chat_model(model, model_provider=provider)
    return init_chat_model(model)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_llm.py -v`
Expected: PASS — both tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/llm.py tests/fakes.py tests/test_llm.py
git commit -m "feat: add provider-agnostic model factory and fake model test helper"
```

---

### Task 5: Analyst nodes (Customer Research + Product Analytics)

**Files:**
- Create: `src/productagents/agents/__init__.py`
- Create: `src/productagents/agents/customer_research.py`
- Create: `src/productagents/agents/product_analytics.py`
- Test: `tests/test_analysts.py`

**Interfaces:**
- Consumes: `AnalystFindings`, `AnalystReport`, `Evidence`, `Initiative` from `productagents.schemas`; `get_stream_writer` from `langgraph.config`.
- Produces:
  - `customer_research.ANALYST_ID = "customer_research"`, `customer_research.ROLE = "Customer Research Analyst"`
  - `async def customer_research.customer_research_node(state: dict, model) -> dict` returning `{"reports": [AnalystReport]}`.
  - `product_analytics.ANALYST_ID = "product_analytics"`, `product_analytics.ROLE = "Product Analytics Analyst"`
  - `async def product_analytics.product_analytics_node(state: dict, model) -> dict` returning `{"reports": [AnalystReport]}`.
  - On LLM failure each node returns a single `AnalystReport` with `failed=True` and empty findings/signals.
  - `state` is expected to contain keys `"initiative": Initiative` and `"evidence": Evidence`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_analysts.py`:

```python
import pytest

from productagents.agents.customer_research import customer_research_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.schemas import AnalystFindings, Evidence, Initiative
from tests.fakes import FakeChatModel


@pytest.fixture
def state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "evidence": Evidence(
            scenario="sample",
            customer_feedback="Enterprises demand SSO.",
            product_analytics={"onboarding_drop_off_rate": 0.3},
        ),
    }


async def test_customer_research_returns_report(state):
    model = FakeChatModel(
        {AnalystFindings: AnalystFindings(findings=["demand for SSO"], signals=["18 tickets"])}
    )
    result = await customer_research_node(state, model)
    reports = result["reports"]
    assert len(reports) == 1
    report = reports[0]
    assert report.analyst == "customer_research"
    assert report.role == "Customer Research Analyst"
    assert report.findings == ["demand for SSO"]
    assert report.failed is False


async def test_product_analytics_returns_report(state):
    model = FakeChatModel(
        {AnalystFindings: AnalystFindings(findings=["30% drop-off"], signals=["funnel data"])}
    )
    result = await product_analytics_node(state, model)
    report = result["reports"][0]
    assert report.analyst == "product_analytics"
    assert report.role == "Product Analytics Analyst"
    assert report.findings == ["30% drop-off"]


async def test_analyst_failure_yields_degraded_report(state):
    model = FakeChatModel({AnalystFindings: RuntimeError("LLM down")})
    result = await customer_research_node(state, model)
    report = result["reports"][0]
    assert report.failed is True
    assert report.findings == []
    assert report.signals == []
    assert report.analyst == "customer_research"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_analysts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.agents'`.

- [ ] **Step 3: Implement the analyst nodes**

Create `src/productagents/agents/__init__.py`:

```python
```

(empty file)

Create `src/productagents/agents/customer_research.py`:

```python
"""Customer Research Analyst node: reads qualitative customer evidence."""

from langgraph.config import get_stream_writer

from productagents.schemas import AnalystFindings, AnalystReport, Evidence, Initiative

ANALYST_ID = "customer_research"
ROLE = "Customer Research Analyst"


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
    writer = get_stream_writer()
    writer({"node": ANALYST_ID, "status": "reading customer evidence…"})
    structured = model.with_structured_output(AnalystFindings)
    try:
        findings = await structured.ainvoke(
            _prompt(state["initiative"], state["evidence"])
        )
        report = AnalystReport(
            analyst=ANALYST_ID,
            role=ROLE,
            findings=findings.findings,
            signals=findings.signals,
        )
        writer({"node": ANALYST_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": ANALYST_ID, "status": f"failed: {exc}"})
        report = AnalystReport(
            analyst=ANALYST_ID, role=ROLE, findings=[], signals=[], failed=True
        )
    return {"reports": [report]}
```

Create `src/productagents/agents/product_analytics.py`:

```python
"""Product Analytics Analyst node: reads quantitative usage evidence."""

import json

from langgraph.config import get_stream_writer

from productagents.schemas import AnalystFindings, AnalystReport, Evidence, Initiative

ANALYST_ID = "product_analytics"
ROLE = "Product Analytics Analyst"


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
    writer = get_stream_writer()
    writer({"node": ANALYST_ID, "status": "analyzing product metrics…"})
    structured = model.with_structured_output(AnalystFindings)
    try:
        findings = await structured.ainvoke(
            _prompt(state["initiative"], state["evidence"])
        )
        report = AnalystReport(
            analyst=ANALYST_ID,
            role=ROLE,
            findings=findings.findings,
            signals=findings.signals,
        )
        writer({"node": ANALYST_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": ANALYST_ID, "status": f"failed: {exc}"})
        report = AnalystReport(
            analyst=ANALYST_ID, role=ROLE, findings=[], signals=[], failed=True
        )
    return {"reports": [report]}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_analysts.py -v`
Expected: PASS — all three tests pass.

> Note: `get_stream_writer()` works outside a graph run (it returns a no-op writer when there is no active stream), so these unit tests need no graph context.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/__init__.py src/productagents/agents/customer_research.py src/productagents/agents/product_analytics.py tests/test_analysts.py
git commit -m "feat: add customer research and product analytics analyst nodes"
```

---

### Task 6: Strategist node

**Files:**
- Create: `src/productagents/agents/strategist.py`
- Test: `tests/test_strategist.py`

**Interfaces:**
- Consumes: `AnalystReport`, `Initiative`, `Recommendation` from `productagents.schemas`; `get_stream_writer`.
- Produces:
  - `strategist.NODE_ID = "strategist"`
  - `async def strategist.strategist_node(state: dict, model) -> dict` returning `{"recommendation": Recommendation}`.
  - `state` is expected to contain `"initiative": Initiative` and `"reports": list[AnalystReport]`.
  - On LLM failure returns a `Recommendation` with `confidence=0.0` and recommendation text noting the failure.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_strategist.py`:

```python
from productagents.agents.strategist import strategist_node
from productagents.schemas import AnalystReport, Initiative, Recommendation
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "reports": [
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["strong enterprise demand"],
                signals=["18 tickets"],
            ),
            AnalystReport(
                analyst="product_analytics",
                role="Product Analytics Analyst",
                findings=["30% onboarding drop-off"],
                signals=["funnel data"],
            ),
        ],
    }


async def test_strategist_returns_recommendation():
    expected = Recommendation(
        recommendation="Build SSO this quarter",
        confidence=0.82,
        rationale="Demand plus measurable onboarding friction.",
        expected_outcomes=["unblock enterprise deals"],
    )
    model = FakeChatModel({Recommendation: expected})
    result = await strategist_node(_state(), model)
    assert result["recommendation"] == expected


async def test_strategist_failure_yields_zero_confidence():
    model = FakeChatModel({Recommendation: RuntimeError("LLM down")})
    result = await strategist_node(_state(), model)
    rec = result["recommendation"]
    assert rec.confidence == 0.0
    assert "unable" in rec.recommendation.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_strategist.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.agents.strategist'`.

- [ ] **Step 3: Implement the strategist node**

Create `src/productagents/agents/strategist.py`:

```python
"""Product Strategist node: synthesizes analyst reports into a recommendation."""

from langgraph.config import get_stream_writer

from productagents.schemas import AnalystReport, Initiative, Recommendation

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


def _prompt(initiative: Initiative, reports: list[AnalystReport]) -> str:
    return (
        "You are a Product Strategist. Synthesize the analyst reports below into "
        "a single recommendation for the initiative. Provide a recommendation, a "
        "confidence score between 0 and 1, a rationale, and expected outcomes.\n\n"
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
        f"Analyst reports:\n{_format_reports(reports)}\n"
    )


async def strategist_node(state: dict, model) -> dict:
    writer = get_stream_writer()
    writer({"node": NODE_ID, "status": "synthesizing recommendation…"})
    structured = model.with_structured_output(Recommendation)
    try:
        recommendation = await structured.ainvoke(
            _prompt(state["initiative"], state["reports"])
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
Expected: PASS — both tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/agents/strategist.py tests/test_strategist.py
git commit -m "feat: add product strategist node"
```

---

### Task 7: Graph assembly

**Files:**
- Create: `src/productagents/graph.py`
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: the three node functions; `Initiative`, `Evidence`, `AnalystReport`, `Recommendation` from `productagents.schemas`.
- Produces:
  - `class GraphState(TypedDict)` with `initiative: Initiative`, `evidence: Evidence`, `reports: Annotated[list[AnalystReport], operator.add]`, `recommendation: Recommendation | None`.
  - `build_graph(model)` → a compiled LangGraph runnable. Both analysts run in parallel from `START`; the strategist runs after both and emits the recommendation; then `END`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_graph.py`:

```python
from productagents.graph import build_graph
from productagents.schemas import (
    AnalystFindings,
    Evidence,
    Initiative,
    Recommendation,
)
from tests.fakes import FakeChatModel


def _model():
    return FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["finding"], signals=["signal"]),
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
        "recommendation": None,
    }


async def test_graph_runs_both_analysts_then_strategist():
    graph = build_graph(_model())
    final = await graph.ainvoke(_initial_state())

    assert len(final["reports"]) == 2
    analysts = {r.analyst for r in final["reports"]}
    assert analysts == {"customer_research", "product_analytics"}
    assert final["recommendation"].recommendation == "Build it"
    assert final["recommendation"].confidence == 0.75
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_graph.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.graph'`.

- [ ] **Step 3: Implement the graph**

Create `src/productagents/graph.py`:

```python
"""LangGraph assembly: parallel analysts fanning into the strategist."""

import operator
from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from productagents.agents.customer_research import customer_research_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.strategist import strategist_node
from productagents.schemas import AnalystReport, Evidence, Initiative, Recommendation


class GraphState(TypedDict):
    initiative: Initiative
    evidence: Evidence
    reports: Annotated[list[AnalystReport], operator.add]
    recommendation: Recommendation | None


def build_graph(model):
    """Compile the decision graph using the injected chat model."""
    graph = StateGraph(GraphState)
    graph.add_node("customer_research", partial(customer_research_node, model=model))
    graph.add_node("product_analytics", partial(product_analytics_node, model=model))
    graph.add_node("strategist", partial(strategist_node, model=model))

    graph.add_edge(START, "customer_research")
    graph.add_edge(START, "product_analytics")
    graph.add_edge("customer_research", "strategist")
    graph.add_edge("product_analytics", "strategist")
    graph.add_edge("strategist", END)

    return graph.compile()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_graph.py -v`
Expected: PASS — the strategist sees both reports and a recommendation is produced.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/graph.py tests/test_graph.py
git commit -m "feat: assemble parallel analyst -> strategist langgraph"
```

---

### Task 8: Decision-record persistence (organizational-memory stub)

**Files:**
- Create: `src/productagents/memory.py`
- Test: `tests/test_memory.py`

**Interfaces:**
- Consumes: `DecisionRecord` from `productagents.schemas`.
- Produces:
  - `DEFAULT_LOG_PATH: pathlib.Path = Path("decisions.jsonl")`
  - `record_decision(record: DecisionRecord, path: Path | None = None) -> None` — appends one JSON line.
  - `read_decisions(path: Path | None = None) -> list[DecisionRecord]` — reads all records back (empty list if file absent).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_memory.py`:

```python
from productagents.memory import read_decisions, record_decision
from productagents.schemas import (
    AnalystReport,
    DecisionRecord,
    Initiative,
    Recommendation,
)


def _record():
    return DecisionRecord(
        initiative=Initiative(title="Add SSO", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["f"],
                signals=["s"],
            )
        ],
        timestamp="2026-06-19T12:00:00+00:00",
    )


def test_record_then_read_round_trips(tmp_path):
    path = tmp_path / "decisions.jsonl"
    record = _record()
    record_decision(record, path=path)
    restored = read_decisions(path=path)
    assert restored == [record]


def test_records_append(tmp_path):
    path = tmp_path / "decisions.jsonl"
    record_decision(_record(), path=path)
    record_decision(_record(), path=path)
    assert len(read_decisions(path=path)) == 2


def test_read_missing_file_returns_empty(tmp_path):
    assert read_decisions(path=tmp_path / "nope.jsonl") == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_memory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.memory'`.

- [ ] **Step 3: Implement persistence**

Create `src/productagents/memory.py`:

```python
"""Append-only decision log — the organizational-memory stub for the slice."""

from pathlib import Path

from productagents.schemas import DecisionRecord

DEFAULT_LOG_PATH = Path("decisions.jsonl")


def _path(path: Path | None) -> Path:
    return path if path is not None else DEFAULT_LOG_PATH


def record_decision(record: DecisionRecord, path: Path | None = None) -> None:
    """Append one decision record as a JSON line."""
    target = _path(path)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")


def read_decisions(path: Path | None = None) -> list[DecisionRecord]:
    """Read all decision records; return [] if the log does not exist."""
    target = _path(path)
    if not target.is_file():
        return []
    records = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(DecisionRecord.model_validate_json(line))
    return records
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: PASS — all three tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/memory.py tests/test_memory.py
git commit -m "feat: add append-only decision log persistence"
```

---

### Task 9: Normalized streaming runner

**Files:**
- Create: `src/productagents/runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: a compiled graph from `build_graph(...)`; `Initiative`, `Evidence`, `AnalystReport`, `Recommendation` from `productagents.schemas`.
- Produces (decouples the TUI from LangGraph's chunk format):
  - `@dataclass ProgressEvent(node: str, message: str)`
  - `@dataclass NodeCompleteEvent(node: str, report: AnalystReport)`
  - `@dataclass FinishedEvent(recommendation: Recommendation | None, reports: list[AnalystReport])`
  - `async def run_decision(graph, initiative: Initiative, evidence: Evidence) -> AsyncIterator[ProgressEvent | NodeCompleteEvent | FinishedEvent]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_runner.py`:

```python
from productagents.graph import build_graph
from productagents.runner import (
    FinishedEvent,
    NodeCompleteEvent,
    ProgressEvent,
    run_decision,
)
from productagents.schemas import (
    AnalystFindings,
    Evidence,
    Initiative,
    Recommendation,
)
from tests.fakes import FakeChatModel


def _graph():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
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


async def test_run_decision_emits_progress_completion_and_finished():
    graph = _graph()
    initiative, evidence = _inputs()

    events = [e async for e in run_decision(graph, initiative, evidence)]

    progress = [e for e in events if isinstance(e, ProgressEvent)]
    completions = [e for e in events if isinstance(e, NodeCompleteEvent)]
    finished = [e for e in events if isinstance(e, FinishedEvent)]

    assert progress  # at least one in-node progress update
    assert {c.report.analyst for c in completions} == {
        "customer_research",
        "product_analytics",
    }
    assert len(finished) == 1
    assert finished[0].recommendation.recommendation == "Build it"
    assert len(finished[0].reports) == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.runner'`.

- [ ] **Step 3: Implement the runner**

Create `src/productagents/runner.py`:

```python
"""Normalize LangGraph's streamed chunks into plain UI-facing events."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from productagents.schemas import AnalystReport, Evidence, Initiative, Recommendation


@dataclass
class ProgressEvent:
    node: str
    message: str


@dataclass
class NodeCompleteEvent:
    node: str
    report: AnalystReport


@dataclass
class FinishedEvent:
    recommendation: Recommendation | None
    reports: list[AnalystReport]


async def run_decision(
    graph, initiative: Initiative, evidence: Evidence
) -> AsyncIterator[ProgressEvent | NodeCompleteEvent | FinishedEvent]:
    """Stream a decision run, yielding normalized events.

    Consumes `graph.astream(..., stream_mode=["updates", "custom"])`, where each
    streamed item is a `(mode, chunk)` tuple: `custom` chunks are the dicts
    emitted by nodes via `get_stream_writer()`, and `updates` chunks map a node
    name to the partial state it returned.
    """
    initial_state = {
        "initiative": initiative,
        "evidence": evidence,
        "reports": [],
        "recommendation": None,
    }
    collected_reports: list[AnalystReport] = []
    recommendation: Recommendation | None = None

    async for mode, chunk in graph.astream(
        initial_state, stream_mode=["updates", "custom"]
    ):
        if mode == "custom":
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
                if node_state.get("recommendation") is not None:
                    recommendation = node_state["recommendation"]

    yield FinishedEvent(recommendation=recommendation, reports=collected_reports)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_runner.py -v`
Expected: PASS.

> If `astream` with a list `stream_mode` yields a shape other than `(mode, chunk)` tuples in the installed LangGraph version, this single function is the only place to adjust — the test will catch a mismatch.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/runner.py tests/test_runner.py
git commit -m "feat: add normalized streaming runner over the decision graph"
```

---

### Task 10: Textual TUI + entry point

**Files:**
- Create: `src/productagents/tui/__init__.py`
- Create: `src/productagents/tui/app.py`
- Create: `src/productagents/tui/app.tcss`
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `run_decision`, `ProgressEvent`, `NodeCompleteEvent`, `FinishedEvent` from `productagents.runner`; `load_scenario` from `productagents.evidence`; `record_decision` from `productagents.memory`; `build_graph` from `productagents.graph`; `get_model` from `productagents.llm`; `Initiative`, `DecisionRecord` from `productagents.schemas`.
- Produces:
  - `class ProductAgentsApp(App)` — constructed as `ProductAgentsApp(runner, evidence, *, recorder=record_decision, scenario="sample")` where `runner(initiative, evidence)` returns the async iterator from `run_decision` (bound to a graph) and `evidence` is a preloaded `Evidence`.
  - `def main() -> None` — entry point wired in `pyproject.toml` `[project.scripts]`; builds the real model + graph, loads the `sample` scenario, and runs the app.

- [ ] **Step 1: Write the failing test**

Create `tests/test_tui.py`:

```python
from functools import partial

from productagents.graph import build_graph
from productagents.runner import run_decision
from productagents.schemas import AnalystFindings, Evidence, Recommendation
from productagents.tui.app import ProductAgentsApp
from tests.fakes import FakeChatModel


def _runner_and_evidence():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"]),
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


async def test_app_renders_recommendation_and_records(tmp_path):
    runner, evidence = _runner_and_evidence()
    log_path = tmp_path / "decisions.jsonl"
    recorded = []

    def recorder(record):
        recorded.append(record)

    app = ProductAgentsApp(runner, evidence, recorder=recorder, scenario="sample")

    async with app.run_test() as pilot:
        await pilot.app.query_one("#initiative-title").focus()
        await pilot.app.query_one("#initiative-title").action_submit() if False else None
        # Enter an initiative and submit
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.pause()
        # Let the worker finish streaming
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        result_text = pilot.app.query_one("#strategist").renderable
        assert "Build SSO now" in str(result_text)

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO now"
    assert recorded[0].initiative.title == "Add SSO"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tui.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'productagents.tui'`.

- [ ] **Step 3: Implement the TUI**

Create `src/productagents/tui/__init__.py`:

```python
```

(empty file)

Create `src/productagents/tui/app.tcss`:

```css
Screen {
    layout: vertical;
}

#initiative-title {
    dock: top;
    margin: 1 1 0 1;
}

#panels {
    height: 1fr;
}

.panel {
    border: round $primary;
    padding: 1;
    margin: 1;
    height: 1fr;
}

#strategist {
    border: round $success;
}
```

Create `src/productagents/tui/app.py`:

```python
"""Textual TUI for running a ProductAgents decision and showing it live."""

from datetime import datetime, timezone
from functools import partial

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, Static

from productagents.evidence import load_scenario
from productagents.graph import build_graph
from productagents.llm import get_model
from productagents.memory import record_decision
from productagents.runner import (
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

    def __init__(self, runner, evidence, *, recorder=record_decision, scenario="sample"):
        super().__init__()
        self._runner = runner
        self._evidence = evidence
        self._recorder = recorder
        self._scenario = scenario

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(
            placeholder="Describe the initiative and press Enter…",
            id="initiative-title",
        )
        with Horizontal(id="panels"):
            yield Static("Waiting…", id="customer_research", classes="panel")
            yield Static("Waiting…", id="product_analytics", classes="panel")
            yield Static("Waiting…", id="strategist", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        for node_id, role in _PANELS.items():
            self.query_one(f"#{node_id}", Static).border_title = role

    def on_input_submitted(self, message: Input.Submitted) -> None:
        title = message.value.strip()
        if not title:
            return
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._run(Initiative(title=title, description=title))

    @work(exclusive=True)
    async def _run(self, initiative: Initiative) -> None:
        recommendation = None
        reports = []
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
            elif isinstance(event, FinishedEvent):
                recommendation = event.recommendation
                reports = event.reports
                self._render_recommendation(recommendation)

        if recommendation is not None:
            self._recorder(
                DecisionRecord(
                    initiative=initiative,
                    recommendation=recommendation,
                    reports=reports,
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


def main() -> None:
    graph = build_graph(get_model())
    evidence = load_scenario("sample")
    app = ProductAgentsApp(partial(run_decision, graph), evidence, scenario="sample")
    app.run()
```

- [ ] **Step 4: Simplify the test now that the API is known**

Replace the body of `test_app_renders_recommendation_and_records` in `tests/test_tui.py` with the cleaned-up version (the earlier draft had an exploratory no-op line):

```python
async def test_app_renders_recommendation_and_records(tmp_path):
    runner, evidence = _runner_and_evidence()
    recorded = []

    def recorder(record):
        recorded.append(record)

    app = ProductAgentsApp(runner, evidence, recorder=recorder, scenario="sample")

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        result_text = pilot.app.query_one("#strategist").renderable
        assert "Build SSO now" in str(result_text)

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO now"
    assert recorded[0].initiative.title == "Add SSO"
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_tui.py -v`
Expected: PASS — the strategist panel shows "Build SSO now" and exactly one decision is recorded.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS — every test from Tasks 1–10 passes.

- [ ] **Step 7: Commit**

```bash
git add src/productagents/tui/__init__.py src/productagents/tui/app.py src/productagents/tui/app.tcss tests/test_tui.py
git commit -m "feat: add textual tui and entry point for live decision runs"
```

---

### Task 11: Usage docs + manual launch verification

**Files:**
- Modify: `README.md` (append a "Running the slice" section)
- Create: `.gitignore` entry for `decisions.jsonl`

**Interfaces:**
- Consumes: the `productagents` entry point from Task 10.
- Produces: documentation only; no code interfaces.

- [ ] **Step 1: Ignore the local decision log**

Append a line to `.gitignore` (the repo already has one):

```text
decisions.jsonl
```

- [ ] **Step 2: Document how to run the slice**

Append to `README.md`:

```markdown
## Running the Slice (first milestone)

This repository currently implements a thin end-to-end slice: two analysts
(Customer Research + Product Analytics) evaluate a bundled evidence scenario in
parallel and a strategist produces a recommendation, shown live in a TUI.

### Setup

```bash
uv sync
```

### Configure a model

Model selection is provider-agnostic. Set the model via environment variables
(defaults to `anthropic:claude-sonnet-4-6`):

```bash
export PRODUCTAGENTS_MODEL="anthropic:claude-sonnet-4-6"
# Provide the matching provider API key, e.g.:
export ANTHROPIC_API_KEY="sk-..."
```

To use another provider, set both variables, e.g.:

```bash
export PRODUCTAGENTS_MODEL="gpt-5.5"
export PRODUCTAGENTS_MODEL_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
```

### Run

```bash
uv run productagents
```

Type an initiative (e.g. "Add enterprise SSO") and press Enter. The analyst
panels update live and the strategist panel shows the final recommendation.
Each run appends a record to `decisions.jsonl`.

### Test

```bash
uv run pytest
```

All tests run offline with a fake model — no API key required.
```

- [ ] **Step 3: Verify the test suite is green**

Run: `uv run pytest -v`
Expected: PASS — full suite green.

- [ ] **Step 4: Manually verify the app launches**

Run: `uv run productagents` (requires a valid API key for the configured provider).
Expected: the TUI opens with an input box and three panels. Enter an initiative, press Enter, watch the analyst panels populate and the strategist panel render a recommendation. Press Ctrl+C / `q` to quit. Confirm a new line was appended to `decisions.jsonl`.

> If no API key is available in the environment, skip the live launch and rely on the green test suite; note this in the task hand-off.

- [ ] **Step 5: Commit**

```bash
git add README.md .gitignore
git commit -m "docs: document running and testing the thin slice"
```

---

## Self-Review

**1. Spec coverage**

- UV + Python 3.14 scaffolding → Task 1. ✓
- Provider-agnostic LLM via `init_chat_model`, env-selected → Task 4 + Global Constraints. ✓
- LangGraph `StateGraph`, two parallel analysts → strategist → Task 7. ✓
- Customer Research + Product Analytics analysts → Task 5; strategist → Task 6. ✓
- Strongly-typed Pydantic schemas, `confidence ∈ [0,1]` → Task 2. ✓
- Mock evidence as named scenarios → Task 3 (bundled `sample`). ✓
- Textual TUI with live progress + final recommendation → Task 10. ✓
- Lightweight `decisions.jsonl` memory, no reflection loop → Task 8 (+ used in Task 10). ✓
- Error handling: analyst degrade (`failed=True`) → Task 5; strategist degrade → Task 6; evidence errors → Task 3; model/key surfaced at launch via `get_model()` raising → Task 4/10. ✓
- Tests with fake model, no network → fake in Task 4, used Tasks 5–10. ✓
- Streaming integration isolated for testability → Task 9. ✓
- Out-of-scope items (debate, risk team, governance, reflection, real integrations, checkpointing) correctly absent. ✓

**2. Placeholder scan**

No "TBD"/"TODO"/"handle edge cases"/"similar to Task N". Every code step contains complete code; the one exploratory line in the first draft of the TUI test is explicitly replaced in Task 10 Step 4. ✓

**3. Type consistency**

- `AnalystFindings(findings, signals)` is the LLM output in Tasks 2/5; analysts wrap it into `AnalystReport(analyst, role, findings, signals, failed)` — consistent across Tasks 5, 6, 7, 9, 10. ✓
- `Recommendation(recommendation, confidence, rationale, expected_outcomes)` identical in Tasks 2, 6, 7, 9, 10. ✓
- `GraphState.reports` uses `Annotated[list[AnalystReport], operator.add]`; analyst nodes return `{"reports": [report]}` (single-item lists) — reducer concatenates to 2. ✓
- Runner events (`ProgressEvent.node/message`, `NodeCompleteEvent.node/report`, `FinishedEvent.recommendation/reports`) match their consumption in Task 10. ✓
- `run_decision(graph, initiative, evidence)` signature matches `partial(run_decision, graph)` usage in Tasks 10/11 and tests. ✓
- `record_decision(record, path=None)` matches recorder usage (Task 10 injects a custom recorder taking a single `record`). ✓

No gaps found.
