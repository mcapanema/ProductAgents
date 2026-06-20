# Live Evidence Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Layer 1 (Evidence Collection) from a single hard-wired bundled-scenario loader into a small pluggable-source layer — a `ScenarioSource` and a new filesystem `DirectorySource` behind one interface, with per-piece provenance threaded into the decision record and a TUI prompt to choose the source before each run.

**Architecture:** Introduce an `EvidenceSource` protocol with a `collect() -> Evidence` method. Refactor today's `load_scenario` into a `ScenarioSource` that implements it (keeping `load_scenario` as a thin backward-compatible wrapper), add a `DirectorySource` that reads the same five evidence files from any directory, and add a `collect_evidence(spec)` resolver that maps a user-typed string to the right source (known scenario name → `ScenarioSource`; existing directory path → `DirectorySource`). Every loaded field records an `EvidenceSourceRef` (field, source label, file location) on `Evidence.sources`; the TUI shows this provenance and persists it on the `DecisionRecord`. The TUI gains a second input so the user picks the evidence source per run; analysts and the rest of the graph are unchanged because they still receive a fully-resolved `Evidence`.

**Tech Stack:** Python ≥ 3.14, uv, Pydantic v2, LangGraph, Textual TUI. Fully offline tests via `tests/fakes.py::FakeChatModel` and `tmp_path` directories. `asyncio_mode = "auto"`.

## Global Constraints

- Python ≥ 3.14; managed with **uv** (`uv run pytest`, `uv run productagents`). No Conda.
- **Nodes/boundaries degrade, never crash.** Evidence resolution errors must surface as a visible message, never an unhandled exception that aborts a run.
- All tests run **offline** — no network, no API key. Use `FakeChatModel` for the model and `tmp_path` for evidence directories.
- **Backward compatibility:** `load_scenario(name, base_dir=None) -> Evidence` must keep its current signature and behavior (every existing caller and test depends on it). New fields on `Evidence` and `DecisionRecord` must have defaults so existing `decisions.jsonl` records still deserialize.
- Follow existing conventions: Pydantic models in `schemas.py`; the five evidence filenames are the module constants `_FEEDBACK_FILE`, `_ANALYTICS_FILE`, `_MARKET_FILE`, `_BUSINESS_FILE`, `_TECHNICAL_FILE` in `evidence.py`. `customer_feedback.md` + `product_analytics.json` are required; the other three are optional and default to `""` / `{}`.
- Test files live in `tests/`, named `test_<area>.py`; `async def test_*` needs no decorator. `uv run pytest` auto-runs coverage.
- Keep `#initiative-title` the **first** `Input` in the TUI `compose()` so it retains default focus (existing TUI tests press Enter expecting the initiative to submit).

## File Structure

- `src/productagents/schemas.py` — add `EvidenceSourceRef`; add `sources: list[EvidenceSourceRef]` to `Evidence`; add `evidence_sources: list[EvidenceSourceRef]` to `DecisionRecord`. (Tasks 1.)
- `src/productagents/evidence.py` — add `EvidenceSource` protocol, a shared `_collect_from_dir` reader that builds provenance, `ScenarioSource`, `DirectorySource`, and `collect_evidence` resolver; refactor `load_scenario` to delegate to `ScenarioSource`. (Tasks 2–4.)
- `src/productagents/tui/app.py` — add an `#evidence-source` input, resolve evidence per run via an injected `collector`, render provenance in a new panel, and persist `evidence_sources` on the `DecisionRecord`. (Tasks 5–6.)
- `README.md`, `CLAUDE.md` — document the source picker, the `DirectorySource` file layout, and provenance. (Task 7.)
- Tests: `tests/test_schemas.py` (Task 1), `tests/test_evidence.py` (Tasks 2–4), `tests/test_tui.py` (Tasks 5–6).

---

### Task 1: Provenance schemas

**Files:**
- Modify: `src/productagents/schemas.py:15-23` (the `Evidence` model) and `src/productagents/schemas.py:158-169` (the `DecisionRecord` model)
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `EvidenceSourceRef(field: str, source: str, location: str)` — a Pydantic model. `field` is the `Evidence` field name (e.g. `"customer_feedback"`), `source` is a label like `"scenario:sample"` or `"directory:/data/q3"`, `location` is the concrete origin (a file path string).
  - `Evidence.sources: list[EvidenceSourceRef]` — defaults to `[]`.
  - `DecisionRecord.evidence_sources: list[EvidenceSourceRef]` — defaults to `[]`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_schemas.py`:

```python
def test_evidence_source_ref_and_provenance_defaults():
    from productagents.schemas import (
        DecisionRecord,
        Evidence,
        EvidenceSourceRef,
        Initiative,
        Recommendation,
    )

    # Evidence.sources defaults to empty and round-trips through JSON.
    ev = Evidence(scenario="s", customer_feedback="f", product_analytics={"x": 1})
    assert ev.sources == []

    ref = EvidenceSourceRef(
        field="customer_feedback",
        source="directory:/data/q3",
        location="/data/q3/customer_feedback.md",
    )
    ev2 = Evidence(
        scenario="s",
        customer_feedback="f",
        product_analytics={"x": 1},
        sources=[ref],
    )
    assert Evidence.model_validate_json(ev2.model_dump_json()).sources[0].field == (
        "customer_feedback"
    )

    # DecisionRecord.evidence_sources defaults to empty (back-compat for old records).
    record = DecisionRecord(
        initiative=Initiative(title="t", description="d"),
        recommendation=Recommendation(
            recommendation="r", confidence=0.5, rationale="x", expected_outcomes=["o"]
        ),
        reports=[],
        timestamp="2026-06-20T00:00:00+00:00",
    )
    assert record.evidence_sources == []
    record2 = record.model_copy(update={"evidence_sources": [ref]})
    assert DecisionRecord.model_validate_json(
        record2.model_dump_json()
    ).evidence_sources[0].source == "directory:/data/q3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas.py::test_evidence_source_ref_and_provenance_defaults -v`
Expected: FAIL with `ImportError` (cannot import `EvidenceSourceRef`).

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/schemas.py`, add the new model immediately **above** the `Evidence` class (so `Evidence` can reference it):

```python
class EvidenceSourceRef(BaseModel):
    """Where one piece of evidence came from, for traceability."""

    field: str = Field(description="The Evidence field this piece populated.")
    source: str = Field(description="Source label, e.g. 'scenario:sample' or 'directory:/data/q3'.")
    location: str = Field(description="Concrete origin, e.g. the file path the data was read from.")
```

Then add the `sources` field to `Evidence` (after `technical_context`):

```python
    technical_context: str = ""
    sources: list[EvidenceSourceRef] = Field(default_factory=list)
```

Then add `evidence_sources` to `DecisionRecord` (after `prior_lessons`, before `timestamp`):

```python
    prior_lessons: list[str] = Field(default_factory=list)
    evidence_sources: list[EvidenceSourceRef] = Field(default_factory=list)
    timestamp: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: PASS (the new test and all existing schema tests).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/schemas.py tests/test_schemas.py
git commit -m "feat: add evidence provenance schemas (EvidenceSourceRef)"
```

---

### Task 2: EvidenceSource protocol + ScenarioSource with provenance

**Files:**
- Modify: `src/productagents/evidence.py` (add protocol, shared reader, `ScenarioSource`; refactor `load_scenario`)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `EvidenceSourceRef`, `Evidence` from Task 1.
- Produces:
  - `class EvidenceSource(Protocol)` with `def collect(self) -> Evidence: ...`
  - `_collect_from_dir(directory: Path, *, scenario: str, source_label: str, label: str) -> Evidence` — internal shared reader that reads the five files from `directory` and populates `Evidence.sources`. `scenario` becomes `Evidence.scenario`; `source_label` is the per-ref `source` string; `label` is used in error messages.
  - `class ScenarioSource` with `__init__(self, name: str, base_dir: Path | None = None)` and `collect(self) -> Evidence`.
  - `load_scenario(name, base_dir=None) -> Evidence` now delegates to `ScenarioSource(name, base_dir).collect()` (unchanged signature/behavior).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_evidence.py`:

```python
def test_scenario_source_populates_provenance():
    from productagents.evidence import ScenarioSource

    evidence = ScenarioSource("sample").collect()
    assert evidence.scenario == "sample"
    by_field = {ref.field: ref for ref in evidence.sources}
    # Required fields always have provenance.
    assert by_field["customer_feedback"].source == "scenario:sample"
    assert by_field["customer_feedback"].location.endswith("customer_feedback.md")
    assert by_field["product_analytics"].location.endswith("product_analytics.json")


def test_load_scenario_still_works_and_has_provenance():
    # Backward-compatible wrapper keeps returning Evidence, now with sources.
    evidence = load_scenario("sample")
    assert evidence.customer_feedback.strip() != ""
    assert any(ref.field == "customer_feedback" for ref in evidence.sources)


def test_scenario_source_omits_provenance_for_absent_optional_files(tmp_path):
    from productagents.evidence import ScenarioSource

    scenario = tmp_path / "minimal"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("feedback text")
    (scenario / "product_analytics.json").write_text('{"dau": 100}')
    evidence = ScenarioSource("minimal", base_dir=tmp_path).collect()
    fields = {ref.field for ref in evidence.sources}
    assert fields == {"customer_feedback", "product_analytics"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_evidence.py::test_scenario_source_populates_provenance -v`
Expected: FAIL with `ImportError` (cannot import `ScenarioSource`).

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/evidence.py`, update the import line and add the protocol/sources. Replace the import:

```python
from productagents.schemas import Evidence
```

with:

```python
from typing import Protocol

from productagents.schemas import Evidence, EvidenceSourceRef
```

(Keep the existing `import json` and `from pathlib import Path` lines.)

Add the protocol near the top (after the module constants, before `EvidenceError` is fine):

```python
class EvidenceSource(Protocol):
    """A source that resolves into a fully-populated Evidence object."""

    def collect(self) -> Evidence: ...
```

Add the shared reader (place it after `_parse_json_object`):

```python
def _collect_from_dir(
    directory: Path, *, scenario: str, source_label: str, label: str
) -> Evidence:
    feedback_path = directory / _FEEDBACK_FILE
    analytics_path = directory / _ANALYTICS_FILE
    if not feedback_path.is_file():
        raise EvidenceError(f"Missing {_FEEDBACK_FILE} in {label!r}")
    if not analytics_path.is_file():
        raise EvidenceError(f"Missing {_ANALYTICS_FILE} in {label!r}")

    sources: list[EvidenceSourceRef] = []

    customer_feedback = feedback_path.read_text(encoding="utf-8")
    sources.append(
        EvidenceSourceRef(
            field="customer_feedback",
            source=source_label,
            location=str(feedback_path),
        )
    )
    product_analytics = _parse_json_object(
        analytics_path.read_text(encoding="utf-8"), _ANALYTICS_FILE, label
    )
    sources.append(
        EvidenceSourceRef(
            field="product_analytics", source=source_label, location=str(analytics_path)
        )
    )

    market_intelligence = ""
    market_path = directory / _MARKET_FILE
    if market_path.is_file():
        market_intelligence = market_path.read_text(encoding="utf-8")
        sources.append(
            EvidenceSourceRef(
                field="market_intelligence",
                source=source_label,
                location=str(market_path),
            )
        )

    business_metrics: dict = {}
    business_path = directory / _BUSINESS_FILE
    if business_path.is_file():
        business_metrics = _parse_json_object(
            business_path.read_text(encoding="utf-8"), _BUSINESS_FILE, label
        )
        sources.append(
            EvidenceSourceRef(
                field="business_metrics",
                source=source_label,
                location=str(business_path),
            )
        )

    technical_context = ""
    technical_path = directory / _TECHNICAL_FILE
    if technical_path.is_file():
        technical_context = technical_path.read_text(encoding="utf-8")
        sources.append(
            EvidenceSourceRef(
                field="technical_context",
                source=source_label,
                location=str(technical_path),
            )
        )

    return Evidence(
        scenario=scenario,
        customer_feedback=customer_feedback,
        product_analytics=product_analytics,
        market_intelligence=market_intelligence,
        business_metrics=business_metrics,
        technical_context=technical_context,
        sources=sources,
    )


class ScenarioSource:
    """Reads a named scenario from the bundled (or a custom) scenarios directory."""

    def __init__(self, name: str, base_dir: Path | None = None):
        self.name = name
        self.base_dir = base_dir

    def collect(self) -> Evidence:
        directory = _base(self.base_dir) / self.name
        if not directory.is_dir():
            raise EvidenceError(
                f"Scenario not found: {self.name!r} (looked in {directory})"
            )
        return _collect_from_dir(
            directory,
            scenario=self.name,
            source_label=f"scenario:{self.name}",
            label=self.name,
        )
```

Finally, replace the entire body of the existing `load_scenario` function (`src/productagents/evidence.py:44-86`) with a one-line delegation:

```python
def load_scenario(name: str, base_dir: Path | None = None) -> Evidence:
    return ScenarioSource(name, base_dir).collect()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_evidence.py -v`
Expected: PASS — the three new tests **and** all pre-existing `test_evidence.py` tests (they exercise `load_scenario`, which now delegates to `ScenarioSource`).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/evidence.py tests/test_evidence.py
git commit -m "feat: add EvidenceSource protocol and ScenarioSource with provenance"
```

---

### Task 3: DirectorySource

**Files:**
- Modify: `src/productagents/evidence.py` (add `DirectorySource`)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `_collect_from_dir`, `EvidenceError` from Task 2.
- Produces: `class DirectorySource` with `__init__(self, path: Path)` and `collect(self) -> Evidence`. `Evidence.scenario` is set to the directory's name; provenance `source` labels are `f"directory:{path}"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_evidence.py`:

```python
def test_directory_source_reads_arbitrary_folder(tmp_path):
    from productagents.evidence import DirectorySource

    folder = tmp_path / "q3-data"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("users want SSO")
    (folder / "product_analytics.json").write_text('{"dau": 4200}')
    (folder / "technical_context.md").write_text("auth service is legacy")

    evidence = DirectorySource(folder).collect()
    assert evidence.scenario == "q3-data"
    assert evidence.customer_feedback == "users want SSO"
    assert evidence.product_analytics == {"dau": 4200}
    assert evidence.technical_context == "auth service is legacy"
    by_field = {ref.field: ref for ref in evidence.sources}
    assert by_field["customer_feedback"].source == f"directory:{folder}"
    assert "technical_context" in by_field
    assert "market_intelligence" not in by_field  # absent optional file → no ref


def test_directory_source_missing_dir_raises(tmp_path):
    from productagents.evidence import DirectorySource

    with pytest.raises(EvidenceError):
        DirectorySource(tmp_path / "nope").collect()


def test_directory_source_missing_required_file_raises(tmp_path):
    from productagents.evidence import DirectorySource

    folder = tmp_path / "incomplete"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("feedback only")
    with pytest.raises(EvidenceError):
        DirectorySource(folder).collect()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_evidence.py::test_directory_source_reads_arbitrary_folder -v`
Expected: FAIL with `ImportError` (cannot import `DirectorySource`).

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/evidence.py`, add after the `ScenarioSource` class:

```python
class DirectorySource:
    """Reads evidence files directly from an arbitrary filesystem directory."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def collect(self) -> Evidence:
        if not self.path.is_dir():
            raise EvidenceError(f"Evidence directory not found: {self.path}")
        return _collect_from_dir(
            self.path,
            scenario=self.path.name,
            source_label=f"directory:{self.path}",
            label=str(self.path),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_evidence.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/evidence.py tests/test_evidence.py
git commit -m "feat: add DirectorySource for arbitrary evidence folders"
```

---

### Task 4: collect_evidence resolver

**Files:**
- Modify: `src/productagents/evidence.py` (add `collect_evidence`)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `ScenarioSource`, `DirectorySource`, `list_scenarios`, `EvidenceError`.
- Produces: `collect_evidence(spec: str | None = None, base_dir: Path | None = None) -> Evidence`. Resolution order:
  1. falsy `spec` → `ScenarioSource("sample", base_dir)`,
  2. `spec` in `list_scenarios(base_dir)` → `ScenarioSource(spec, base_dir)`,
  3. `Path(spec).is_dir()` → `DirectorySource(Path(spec))`,
  4. otherwise → raise `EvidenceError`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_evidence.py`:

```python
def test_collect_evidence_defaults_to_sample():
    from productagents.evidence import collect_evidence

    evidence = collect_evidence(None)
    assert evidence.scenario == "sample"
    assert evidence.sources and evidence.sources[0].source == "scenario:sample"


def test_collect_evidence_resolves_known_scenario(tmp_path):
    from productagents.evidence import collect_evidence

    scenario = tmp_path / "alpha"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("f")
    (scenario / "product_analytics.json").write_text('{"x": 1}')
    evidence = collect_evidence("alpha", base_dir=tmp_path)
    assert evidence.scenario == "alpha"
    assert evidence.sources[0].source == "scenario:alpha"


def test_collect_evidence_resolves_directory_path(tmp_path):
    from productagents.evidence import collect_evidence

    folder = tmp_path / "loose-folder"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("f")
    (folder / "product_analytics.json").write_text('{"x": 1}')
    evidence = collect_evidence(str(folder))
    assert evidence.scenario == "loose-folder"
    assert evidence.sources[0].source == f"directory:{folder}"


def test_collect_evidence_unknown_spec_raises():
    from productagents.evidence import collect_evidence

    with pytest.raises(EvidenceError):
        collect_evidence("definitely-not-a-scenario-or-path")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_evidence.py::test_collect_evidence_defaults_to_sample -v`
Expected: FAIL with `ImportError` (cannot import `collect_evidence`).

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/evidence.py`, add at the end of the module:

```python
def collect_evidence(
    spec: str | None = None, base_dir: Path | None = None
) -> Evidence:
    """Resolve a user-supplied source spec to Evidence.

    A falsy spec loads the bundled 'sample' scenario. A spec matching a known
    scenario name loads that scenario; an existing directory path is read as a
    DirectorySource. Anything else raises EvidenceError.
    """
    if not spec:
        return ScenarioSource("sample", base_dir).collect()
    if spec in list_scenarios(base_dir):
        return ScenarioSource(spec, base_dir).collect()
    if Path(spec).is_dir():
        return DirectorySource(Path(spec)).collect()
    raise EvidenceError(
        f"No evidence source for {spec!r}: not a known scenario or a directory"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_evidence.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/productagents/evidence.py tests/test_evidence.py
git commit -m "feat: add collect_evidence resolver for scenario/directory specs"
```

---

### Task 5: TUI per-run evidence collection via source input

**Files:**
- Modify: `src/productagents/tui/app.py` (add `#evidence-source` input, `collector` injection, resolve evidence per run, error handling)
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: `collect_evidence` and `EvidenceError` from `productagents.evidence`; `Evidence` provenance from Tasks 1–4.
- Produces:
  - `ProductAgentsApp.__init__` gains a keyword-only `collector=collect_evidence` parameter (a callable `spec -> Evidence`). The existing positional `evidence` parameter stays and is used as the fallback when the source field is empty.
  - A new `Input` with `id="evidence-source"`, placed **after** `#initiative-title` in `compose()`.
  - `on_input_submitted` ignores submits from any input other than `#initiative-title`, reads the source spec, resolves evidence (fallback to `self._evidence` when empty), and passes the resolved `Evidence` into the worker: `self._run(initiative, evidence)`.
  - `_run(self, initiative, evidence)` uses the passed `evidence` (not `self._evidence`) for the runner call.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tui.py`:

```python
async def test_app_collects_evidence_from_typed_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, default_evidence = _runner_and_evidence()

    folder = tmp_path / "typed-dir"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("typed-dir feedback")
    (folder / "product_analytics.json").write_text('{"dau": 9}')

    seen = {}

    async def capturing_runner(initiative, evidence, **kwargs):
        seen["scenario"] = evidence.scenario
        async for event in runner(initiative, evidence, **kwargs):
            yield event

    from productagents.evidence import collect_evidence

    app = ProductAgentsApp(
        capturing_runner,
        default_evidence,
        collector=collect_evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#evidence-source").value = str(folder)
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()

    assert seen["scenario"] == "typed-dir"


async def test_app_shows_error_for_bad_evidence_source(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, default_evidence = _runner_and_evidence()
    ran = {"called": False}

    async def tracking_runner(initiative, evidence, **kwargs):
        ran["called"] = True
        async for event in runner(initiative, evidence, **kwargs):
            yield event

    from productagents.evidence import collect_evidence

    app = ProductAgentsApp(
        tracking_runner,
        default_evidence,
        collector=collect_evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#evidence-source").value = "/no/such/source/xyz"
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.pause()
        strat_text = str(pilot.app.query_one("#strategist").content)

    assert ran["called"] is False
    assert "Evidence" in strat_text or "evidence" in strat_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tui.py::test_app_collects_evidence_from_typed_directory -v`
Expected: FAIL with `TypeError` (unexpected keyword argument `collector`) or `NoMatches` (`#evidence-source` not found).

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/tui/app.py`:

Update the evidence import line:

```python
from productagents.evidence import EvidenceError, collect_evidence
```

Update `__init__` to accept the collector (add the keyword-only parameter and store it):

```python
    def __init__(
        self,
        runner,
        evidence,
        *,
        collector=collect_evidence,
        recorder=record_decision,
        reader=read_decisions,
        outcome_reader=read_outcomes,
        reflector=None,
        outcome_recorder=record_outcome,
    ):
        super().__init__()
        self._runner = runner
        self._evidence = evidence
        self._collector = collector
        self._recorder = recorder
```

(Leave the rest of `__init__` unchanged.)

In `compose()`, add the source input **immediately after** the `#initiative-title` input:

```python
        yield Input(
            placeholder="Describe the initiative and press Enter…",
            id="initiative-title",
        )
        yield Input(
            placeholder="Evidence source (scenario name or folder path; blank = sample)",
            id="evidence-source",
        )
```

Replace `on_input_submitted` with a version that guards the input id, resolves evidence, and passes it to the worker:

```python
    def on_input_submitted(self, message: Input.Submitted) -> None:
        if message.input.id != "initiative-title":
            return
        title = message.value.strip()
        if not title or self._runner is None:
            return
        spec = self.query_one("#evidence-source", Input).value.strip()
        try:
            evidence = self._collector(spec) if spec else self._evidence
        except EvidenceError as exc:
            self.query_one("#strategist", Static).update(f"Evidence error: {exc}")
            return
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._debate_lines = []
        self._risk_lines = []
        self.query_one("#debate", Static).update("…")
        self.query_one("#risk", Static).update("…")
        self.query_one("#governance", Static).update("…")
        self._run(Initiative(title=title, description=title), evidence)
```

Update the `_run` worker signature and its runner call to use the passed evidence:

```python
    @work(exclusive=True)
    async def _run(self, initiative: Initiative, evidence) -> None:
```

and inside `_run`, change the runner call from `self._evidence` to `evidence`:

```python
        async for event in self._runner(
            initiative,
            evidence,
            portfolio=portfolio,
            outcomes=outcomes,
            approver=self._ask_human,
        ):
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tui.py -v`
Expected: PASS — the two new tests and all pre-existing TUI tests (which leave `#evidence-source` blank and so fall back to the injected `evidence`).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/tui/app.py tests/test_tui.py
git commit -m "feat: let the TUI pick the evidence source per run"
```

---

### Task 6: TUI provenance display + persist evidence_sources

**Files:**
- Modify: `src/productagents/tui/app.py` (add provenance panel, render it, persist `evidence_sources`)
- Test: `tests/test_tui.py`

**Interfaces:**
- Consumes: resolved `Evidence` (with `.sources`) from Task 5; `DecisionRecord.evidence_sources` from Task 1.
- Produces:
  - A new `Static` panel `id="evidence-provenance"` with border title `"Evidence Sources"`, rendered when a run starts.
  - The `DecisionRecord` built in `_run` now includes `evidence_sources=evidence.sources`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tui.py`:

```python
async def test_app_renders_and_records_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, default_evidence = _runner_and_evidence()

    folder = tmp_path / "prov-dir"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("prov feedback")
    (folder / "product_analytics.json").write_text('{"dau": 3}')

    from productagents.evidence import collect_evidence

    recorded = []
    app = ProductAgentsApp(
        runner,
        default_evidence,
        collector=collect_evidence,
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#evidence-source").value = str(folder)
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        prov_text = str(pilot.app.query_one("#evidence-provenance").content)

    assert "customer_feedback" in prov_text
    assert "directory:" in prov_text
    assert len(recorded) == 1
    assert any(
        ref.field == "customer_feedback" for ref in recorded[0].evidence_sources
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tui.py::test_app_renders_and_records_provenance -v`
Expected: FAIL with `NoMatches` (`#evidence-provenance` not found).

- [ ] **Step 3: Write minimal implementation**

In `src/productagents/tui/app.py`:

In `compose()`, add the provenance panel right after the `#evidence-source` input:

```python
        yield Input(
            placeholder="Evidence source (scenario name or folder path; blank = sample)",
            id="evidence-source",
        )
        yield Static("Waiting…", id="evidence-provenance", classes="panel")
```

In `on_mount`, set its border title (add a line alongside the other `border_title` assignments):

```python
        self.query_one(
            "#evidence-provenance", Static
        ).border_title = "Evidence Sources"
```

In `on_input_submitted`, after evidence is successfully resolved and before `self._run(...)`, render provenance:

```python
        prov = "\n".join(f"• {ref.field} ← {ref.source}" for ref in evidence.sources)
        self.query_one("#evidence-provenance", Static).update(prov or "(default)")
```

In `_run`, add `evidence_sources=evidence.sources` to the `DecisionRecord(...)` constructed near the end:

```python
            self._recorder(
                DecisionRecord(
                    initiative=initiative,
                    recommendation=recommendation,
                    reports=reports,
                    debate=debate,
                    risks=risks,
                    governance=governance,
                    prior_lessons=prior_lessons,
                    evidence_sources=evidence.sources,
                    timestamp=datetime.now(UTC).isoformat(),
                )
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tui.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest`
Expected: PASS (all tests, offline).

- [ ] **Step 6: Commit**

```bash
git add src/productagents/tui/app.py tests/test_tui.py
git commit -m "feat: show evidence provenance in the TUI and persist it on the record"
```

---

### Task 7: Documentation

**Files:**
- Modify: `README.md` (the "Running the Slice" section around `README.md:447-467`)
- Modify: `CLAUDE.md` (the architecture diagram and the `evidence.py` / `tui/app.py` data-flow bullets)

**Interfaces:**
- Consumes: the full feature from Tasks 1–6.
- Produces: documentation only — no code, no tests.

- [ ] **Step 1: Update README**

In `README.md`, within the "Running the Slice (first milestone)" section, add a paragraph after the existing evidence description explaining the source picker. Insert after the line ending `…saved (with the full debate transcript, risk assessments, advisory governance verdict, and human decision) to \`decisions.jsonl\`.`:

```markdown
Evidence is pluggable. By default the bundled `sample` scenario is loaded, but
the TUI's second input lets you point a run at a different source before pressing
Enter: type another bundled scenario name, or a filesystem path to any folder
containing the evidence files. A folder is read as a `DirectorySource` and must
contain `customer_feedback.md` and `product_analytics.json` (required) and may
include `market_intelligence.md`, `business_metrics.json`, and
`technical_context.md` (optional). Each piece of evidence records its provenance
(which source and file it came from); the provenance is shown in the TUI's
"Evidence Sources" panel and saved on the decision record.
```

- [ ] **Step 2: Update CLAUDE.md**

In `CLAUDE.md`, update the architecture slice diagram's first stage from `evidence →` to reflect the source layer, and update the `evidence.py` bullet under "Data flow / layers". Replace the existing `evidence.py` bullet:

```markdown
- `evidence.py` — loads a named scenario (markdown + JSON) from `data/scenarios/<name>/`. The TUI loads the bundled `sample` scenario.
```

with:

```markdown
- `evidence.py` — pluggable Layer-1 evidence collection behind an `EvidenceSource` protocol (`collect() -> Evidence`). `ScenarioSource` reads a named scenario from `data/scenarios/<name>/`; `DirectorySource` reads the same five files from any folder. `collect_evidence(spec)` resolves a user-typed string (known scenario name → `ScenarioSource`; existing directory path → `DirectorySource`; blank → bundled `sample`). Every loaded field records an `EvidenceSourceRef` on `Evidence.sources` (provenance), which the TUI persists on the `DecisionRecord`. `load_scenario(name)` remains as a thin wrapper over `ScenarioSource`.
```

Then update the `tui/app.py` bullet to mention the source picker — append to that bullet:

```markdown
 The TUI has a second input for the evidence source (scenario name or folder path; blank = bundled `sample`); it resolves evidence per run via `collect_evidence`, renders the resolved provenance in an "Evidence Sources" panel, and writes `evidence_sources` onto the `DecisionRecord`.
```

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document pluggable evidence sources and provenance"
```

---

## Self-Review

**Spec coverage:**
- EvidenceSource protocol + ScenarioSource refactor → Task 2. ✓
- New filesystem DirectorySource → Task 3. ✓
- Resolver mapping a spec to a source → Task 4. ✓
- Provenance on Evidence + threaded into DecisionRecord → Tasks 1 (schema), 6 (persist). ✓
- TUI prompt to pick the source before each run → Task 5. ✓
- Provenance shown in TUI → Task 6. ✓
- `load_scenario` backward compatibility → Task 2 (delegation; existing `test_evidence.py` re-run). ✓
- Docs → Task 7. ✓

**Placeholder scan:** No TBD/TODO/"handle edge cases" — every code step shows full code; error handling is concrete (`EvidenceError` raised in sources, caught in `on_input_submitted`). ✓

**Type consistency:** `EvidenceSourceRef(field, source, location)` used identically in Task 1 (definition), Task 2 (`_collect_from_dir` construction), and Tasks 5–6 (`ref.field`, `ref.source`). `collect_evidence(spec, base_dir=None)` signature matches its call sites in Task 5 (`self._collector(spec)`) and tests. `_collect_from_dir(directory, *, scenario, source_label, label)` matches both `ScenarioSource.collect` and `DirectorySource.collect` call sites. `ProductAgentsApp.__init__(..., collector=collect_evidence, ...)` matches all test constructions (existing tests omit it → default). `_run(self, initiative, evidence)` matches its single call site in `on_input_submitted`. ✓
