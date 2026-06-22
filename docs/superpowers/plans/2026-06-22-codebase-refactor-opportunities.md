# Codebase Refactor Opportunities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove four categories of duplication/structural drift from the ProductAgents codebase without changing observable behavior, collapsing repeated env-var parsing, JSONL persistence, prompt boilerplate, and the runner/TUI event-dispatch chains into shared, tested helpers.

**Architecture:** Each refactor introduces a small shared helper (or dispatch table) and rewires existing call sites to it. New helpers get their own failing-first unit tests; the existing offline suite (every node, the graph, and the headless TUI) is the regression net that proves the rewired call sites still behave identically. No public function signatures change, so no existing test imports break.

**Tech Stack:** Python ≥ 3.14, uv, pydantic v2, LangGraph, Textual, pytest (`asyncio_mode = "auto"`), coverage gate `--cov-fail-under=90`.

## Global Constraints

- Python ≥ 3.14; managed with **uv** (`uv run pytest`, `uv run productagents`). Never invoke `pip` or `python` directly.
- Tests run **fully offline** — no test may need an API key or network. Use `tests/fakes.py::FakeChatModel` (maps a Pydantic schema class → the instance/`Exception` its `with_structured_output(schema).ainvoke()` returns).
- `asyncio_mode = "auto"` — write `async def test_*` with **no** decorator.
- Coverage gate is **90%** (`--cov-fail-under=90`, configured in `pyproject.toml`). Every new helper and every branch of it must be exercised by a test, or the suite fails.
- **Nodes degrade, never crash** — preserve every existing `try/except Exception` (`# noqa: BLE001`) fallback exactly. No refactor may remove or narrow a degradation path.
- **Behavior-preserving** — these are refactors. The only intentional observable change is the prompt-text unification in Task 4 (documented there); everything else must produce byte-identical output.
- Keep existing public names importable: `get_debate_rounds` (in `agents/debate.py`), `get_judge_threshold` / `get_judge_max_retries` / `DEFAULT_JUDGE_THRESHOLD` / `DEFAULT_JUDGE_MAX_RETRIES` (in `agents/judge.py`), and all `memory.py` / `runner.py` public functions. Tests import these by name.
- Run `graphify update .` after the final task to keep `graphify-out/` current (AST-only, no API cost).

---

## File Structure

| File | Change | Responsibility after change |
| --- | --- | --- |
| `src/productagents/config.py` | Modify | Gains `env_int()` / `env_float()` — the single place env vars are parsed-with-fallback. Still owns `load_env()`. |
| `src/productagents/agents/debate.py` | Modify | `get_debate_rounds()` delegates to `config.env_int`. |
| `src/productagents/agents/judge.py` | Modify | `get_judge_threshold()` / `get_judge_max_retries()` delegate to `config.env_float` / `config.env_int`. |
| `src/productagents/memory.py` | Modify | `record_*` / `read_*` delegate to generic `_append_jsonl` / `_read_jsonl`; one `_path(path, default)` helper. |
| `src/productagents/agents/_format.py` | Modify | Gains `format_initiative()` and `format_recommendation()` shared prompt formatters. |
| `src/productagents/agents/customer_research.py`, `product_analytics.py`, `market.py`, `business.py`, `technical.py`, `debate.py`, `risk.py`, `judge.py`, `governance.py`, `strategist.py`, `reflection.py` | Modify | Prompt builders use `format_initiative()`; risk/judge/governance use `format_recommendation()`. |
| `src/productagents/runner.py` | Modify | Custom-chunk handling becomes a `(key, builder)` dispatch table. |
| `src/productagents/tui/app.py` | Modify | `_run` dispatches events through a `{type: handler}` map; panel-reset extracted to `_reset_panels()`. |
| `tests/test_config.py` | Modify | Add `env_int` / `env_float` unit tests. |
| `tests/test_format.py` | Modify | Add `format_initiative` / `format_recommendation` unit tests. |
| `tests/test_memory.py` | Modify | Add outcome-log round-trip + skip-invalid tests (parity with decisions). |

No new source files — every refactor lands in an existing module, matching the established package layout.

---

## Task 1: Shared env-var parsing helpers

Collapse the three near-identical "read env → parse → clamp → fall back to default" functions (`get_debate_rounds`, `get_judge_threshold`, `get_judge_max_retries`) onto two typed helpers in `config.py`. The public getter functions stay (tests import them) but become one-line delegates.

**Files:**
- Modify: `src/productagents/config.py`
- Modify: `src/productagents/agents/debate.py:35-44`
- Modify: `src/productagents/agents/judge.py:31-52`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `config.env_int(name: str, default: int, *, minimum: int | None = None) -> int` — returns `default` if the var is unset, non-integer, or (when `minimum` given) below `minimum`.
  - `config.env_float(name: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float` — returns `default` if unset, non-float, or outside `[minimum, maximum]` (bounds inclusive, applied only when given).
- Consumes (unchanged public surface): `agents.debate.get_debate_rounds() -> int`, `agents.judge.get_judge_threshold() -> float`, `agents.judge.get_judge_max_retries() -> int`.

- [ ] **Step 1: Write the failing tests for the new helpers**

Add to the end of `tests/test_config.py`:

```python
from productagents.config import env_float, env_int


def test_env_int_default_when_unset(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_X", raising=False)
    assert env_int("PRODUCTAGENTS_X", 2) == 2


def test_env_int_parses_value(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_X", "5")
    assert env_int("PRODUCTAGENTS_X", 2) == 5


def test_env_int_non_integer_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_X", "not-a-number")
    assert env_int("PRODUCTAGENTS_X", 2) == 2


def test_env_int_below_minimum_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_X", "0")
    assert env_int("PRODUCTAGENTS_X", 2, minimum=1) == 2
    monkeypatch.setenv("PRODUCTAGENTS_X", "-3")
    assert env_int("PRODUCTAGENTS_X", 1, minimum=0) == 1


def test_env_int_at_minimum_is_kept(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_X", "0")
    assert env_int("PRODUCTAGENTS_X", 1, minimum=0) == 0


def test_env_float_default_when_unset(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_Y", raising=False)
    assert env_float("PRODUCTAGENTS_Y", 0.7) == 0.7


def test_env_float_parses_value(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_Y", "0.85")
    assert env_float("PRODUCTAGENTS_Y", 0.7) == 0.85


def test_env_float_non_float_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_Y", "garbage")
    assert env_float("PRODUCTAGENTS_Y", 0.7) == 0.7


def test_env_float_out_of_range_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_Y", "1.5")
    assert env_float("PRODUCTAGENTS_Y", 0.7, minimum=0.0, maximum=1.0) == 0.7
    monkeypatch.setenv("PRODUCTAGENTS_Y", "-0.1")
    assert env_float("PRODUCTAGENTS_Y", 0.7, minimum=0.0, maximum=1.0) == 0.7
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_config.py -k "env_int or env_float" -v`
Expected: FAIL with `ImportError: cannot import name 'env_int' from 'productagents.config'`.

- [ ] **Step 3: Implement the helpers in `config.py`**

Append to `src/productagents/config.py` (after `load_env`):

```python
def env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    """Read an int env var, falling back to `default` on absence/parse error.

    When `minimum` is given, values below it also fall back to `default`.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    return value


def env_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """Read a float env var, falling back to `default` on absence/parse error.

    When `minimum`/`maximum` are given, values outside the inclusive range also
    fall back to `default`.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    if maximum is not None and value > maximum:
        return default
    return value
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_config.py -k "env_int or env_float" -v`
Expected: PASS (all 9 new tests green).

- [ ] **Step 5: Rewire `get_debate_rounds` to delegate**

In `src/productagents/agents/debate.py`, add `from productagents.config import env_int` to the imports (next to `import os`), then replace the whole `get_debate_rounds` body (currently lines 35-44):

```python
def get_debate_rounds() -> int:
    """Return the configured number of debate rounds (default 2)."""
    return env_int("PRODUCTAGENTS_DEBATE_ROUNDS", DEFAULT_DEBATE_ROUNDS, minimum=1)
```

Then remove the now-unused `import os` from `debate.py` (it was only used by the old body).

- [ ] **Step 6: Rewire the judge getters to delegate**

In `src/productagents/agents/judge.py`, add `from productagents.config import env_float, env_int` to the imports, then replace the bodies of `get_judge_threshold` (lines 31-40) and `get_judge_max_retries` (lines 43-52):

```python
def get_judge_threshold() -> float:
    """Return the configured pass threshold for both dimensions (default 0.7)."""
    return env_float(
        "PRODUCTAGENTS_JUDGE_THRESHOLD",
        DEFAULT_JUDGE_THRESHOLD,
        minimum=0.0,
        maximum=1.0,
    )


def get_judge_max_retries() -> int:
    """Return the configured max strategist revisions (default 1; 0 = score-only)."""
    return env_int(
        "PRODUCTAGENTS_JUDGE_MAX_RETRIES", DEFAULT_JUDGE_MAX_RETRIES, minimum=0
    )
```

Then remove the now-unused `import os` from `judge.py`.

- [ ] **Step 7: Run the existing getter tests + new tests to verify no regression**

Run: `uv run pytest tests/test_config.py tests/test_debate.py tests/test_judge.py -v`
Expected: PASS. The existing `test_get_debate_rounds_*`, `test_get_judge_threshold_parsing`, and `test_get_judge_max_retries_parsing` tests prove the delegation preserves behavior (including the `0`-and-`-2`-fall-back edge cases).

- [ ] **Step 8: Run the full suite to confirm coverage holds**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%.

- [ ] **Step 9: Commit**

```bash
git add src/productagents/config.py src/productagents/agents/debate.py src/productagents/agents/judge.py tests/test_config.py
git commit -m "refactor: centralize env-var parsing in config.env_int/env_float"
```

---

## Task 2: Deduplicate JSONL persistence

`record_decision`/`record_outcome`, `read_decisions`/`read_outcomes`, and `_path`/`_outcome_path` in `memory.py` are line-for-line identical except for the model class and default path. Collapse onto generic `_append_jsonl` / `_read_jsonl` and a single `_path(path, default)`.

**Files:**
- Modify: `src/productagents/memory.py:14-76`
- Test: `tests/test_memory.py`

**Interfaces:**
- Consumes: `schemas.DecisionRecord`, `schemas.OutcomeRecord` (both expose `.model_dump_json()` and classmethod `.model_validate_json()`).
- Produces (unchanged public surface): `record_decision(record, path=None)`, `read_decisions(path=None) -> list[DecisionRecord]`, `record_outcome(outcome, path=None)`, `read_outcomes(path=None) -> list[OutcomeRecord]`.
- Internal helpers (new): `_path(path: Path | None, default: Path) -> Path`, `_append_jsonl(record, path: Path) -> None`, `_read_jsonl(path: Path, model_cls) -> list`.

- [ ] **Step 1: Write failing parity tests for the outcome log**

`tests/test_memory.py` already covers the decision log. Add the outcome-log equivalents so both paths through the shared helpers are exercised. Append to `tests/test_memory.py`:

```python
from productagents.memory import read_outcomes, record_outcome
from productagents.schemas import OutcomeRecord


def _outcome():
    return OutcomeRecord(
        decision_id="abc123",
        actual_outcomes=["shipped late"],
        prediction_accuracy=0.6,
        lessons_learned=["scope smaller"],
        reflected_at="2026-06-20T12:00:00+00:00",
    )


def test_outcome_record_then_read_round_trips(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    outcome = _outcome()
    record_outcome(outcome, path=path)
    assert read_outcomes(path=path) == [outcome]


def test_read_outcomes_missing_file_returns_empty(tmp_path):
    assert read_outcomes(path=tmp_path / "nope.jsonl") == []


def test_read_outcomes_skips_blank_and_invalid_lines(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    record_outcome(_outcome(), path=path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n")               # blank line skipped
        handle.write("{not valid json}\n")  # invalid line skipped
    assert read_outcomes(path=path) == [_outcome()]
```

- [ ] **Step 2: Run the new tests to verify they pass against the current code**

Run: `uv run pytest tests/test_memory.py -k outcome -v`
Expected: PASS. (These document current behavior; they are the regression net for the refactor that follows — they must stay green after Step 3.)

- [ ] **Step 3: Replace the duplicated functions with shared helpers**

Replace lines 14-76 of `src/productagents/memory.py` (from `def _path` through the end of `read_outcomes`) with:

```python
def _path(path: Path | None, default: Path) -> Path:
    return path if path is not None else default


def _append_jsonl(record, path: Path) -> None:
    """Append one pydantic record as a JSON line."""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")


def _read_jsonl(path: Path, model_cls):
    """Read+validate every JSON line into `model_cls`, skipping malformed lines.

    Returns [] if the file does not exist. Blank lines and schema-incompatible
    lines (e.g. legacy records that predate a schema tightening) are skipped
    rather than aborting the read — "degrade, never crash" at the persistence
    boundary.
    """
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(model_cls.model_validate_json(line))
        except ValidationError:
            continue
    return records


def record_decision(record: DecisionRecord, path: Path | None = None) -> None:
    """Append one decision record as a JSON line."""
    _append_jsonl(record, _path(path, DEFAULT_LOG_PATH))


def read_decisions(path: Path | None = None) -> list[DecisionRecord]:
    """Read all decision records; return [] if the log does not exist."""
    return _read_jsonl(_path(path, DEFAULT_LOG_PATH), DecisionRecord)


def record_outcome(outcome: OutcomeRecord, path: Path | None = None) -> None:
    """Append one outcome record as a JSON line."""
    _append_jsonl(outcome, _path(path, DEFAULT_OUTCOME_LOG_PATH))


def read_outcomes(path: Path | None = None) -> list[OutcomeRecord]:
    """Read all outcome records; return [] if the log does not exist."""
    return _read_jsonl(_path(path, DEFAULT_OUTCOME_LOG_PATH), OutcomeRecord)
```

Leave everything below (the `_STOPWORDS` block, `_tokens`, `select_relevant_lessons`) untouched.

- [ ] **Step 4: Run the memory tests to verify no regression**

Run: `uv run pytest tests/test_memory.py -v`
Expected: PASS — both the pre-existing decision tests (round-trip, append, missing-file, skip-invalid) and the new outcome tests stay green.

- [ ] **Step 5: Run the full suite to confirm coverage holds**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%.

- [ ] **Step 6: Commit**

```bash
git add src/productagents/memory.py tests/test_memory.py
git commit -m "refactor: dedupe JSONL read/write in memory via _read_jsonl/_append_jsonl"
```

---

## Task 3: Shared `format_initiative` prompt formatter

The exact two-line block `Initiative: {title}\nDescription: {description}` is hand-built in 11 prompt builders. Extract it to `_format.py` and apply everywhere. The rendered text is byte-identical, so existing node tests (which key `FakeChatModel` by schema and ignore prompt text) stay green.

**Files:**
- Modify: `src/productagents/agents/_format.py`
- Modify: `src/productagents/agents/customer_research.py`, `product_analytics.py`, `market.py`, `business.py`, `technical.py`, `debate.py`, `risk.py`, `judge.py`, `governance.py`, `strategist.py`, `reflection.py`
- Test: `tests/test_format.py`

**Interfaces:**
- Produces: `_format.format_initiative(initiative: Initiative) -> str` — returns exactly `f"Initiative: {initiative.title}\nDescription: {initiative.description}"` (no trailing newline; callers add their own spacing).
- Consumes: `schemas.Initiative` (`.title`, `.description`).

- [ ] **Step 1: Write the failing test for `format_initiative`**

Add to `tests/test_format.py`:

```python
from productagents.agents._format import format_initiative
from productagents.schemas import Initiative


def test_format_initiative_renders_two_lines():
    out = format_initiative(Initiative(title="Add SSO", description="Enterprise SSO"))
    assert out == "Initiative: Add SSO\nDescription: Enterprise SSO"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_format.py::test_format_initiative_renders_two_lines -v`
Expected: FAIL with `ImportError: cannot import name 'format_initiative'`.

- [ ] **Step 3: Implement `format_initiative` in `_format.py`**

Add to `src/productagents/agents/_format.py` (update the import line and add the function). Change the import line to:

```python
from productagents.schemas import AnalystReport, DebateTurn, Initiative
```

Add the function (above `format_reports_brief`):

```python
def format_initiative(initiative: Initiative) -> str:
    """Render the shared two-line initiative header used by every prompt."""
    return f"Initiative: {initiative.title}\nDescription: {initiative.description}"
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_format.py::test_format_initiative_renders_two_lines -v`
Expected: PASS.

- [ ] **Step 5: Apply `format_initiative` in the five analysts**

In each of `customer_research.py`, `product_analytics.py`, `market.py`, `business.py`, `technical.py`: add `from productagents.agents._format import format_initiative` and replace the two prompt lines

```python
        f"Initiative: {initiative.title}\n"
        f"Description: {initiative.description}\n\n"
```

with

```python
        f"{format_initiative(initiative)}\n\n"
```

For `customer_research.py`, the full resulting `_prompt` is:

```python
def _prompt(initiative: Initiative, evidence: Evidence) -> str:
    return (
        f"You are a {ROLE} evaluating a proposed product initiative.\n\n"
        f"{format_initiative(initiative)}\n\n"
        "Using ONLY the customer feedback below, identify the key customer "
        "pain points and demand signals relevant to this initiative.\n\n"
        f"Customer feedback:\n{evidence.customer_feedback}\n"
    )
```

Apply the identical edit (only the analyst-specific evidence lines differ) to the other four analyst files.

- [ ] **Step 6: Apply `format_initiative` in debate, risk, judge, governance, strategist, reflection**

In each file, add `format_initiative` to the existing `from productagents.agents._format import ...` line (or add the import where there is none — `governance.py`, `strategist.py`, `reflection.py` import other formatters; `reflection.py` currently imports none from `_format`, so add `from productagents.agents._format import format_initiative`). Then replace the `Initiative:` / `Description:` line pair with `f"{format_initiative(initiative)}\n\n"` in each `_prompt`:

- `debate.py::_prompt` → `f"{_PERSONA[side]}\n\n{format_initiative(initiative)}\n\n"` followed by the unchanged `Analyst findings:` block.
- `risk.py::_prompt` → keep the `You are a {role}...` opening line, then `f"{format_initiative(initiative)}\n\n"`, then the unchanged recommendation/findings/transcript lines.
- `judge.py::_prompt` → after the rubric instructions, `f"{format_initiative(initiative)}\n\n"`, then the unchanged recommendation/findings/transcript lines.
- `governance.py::_prompt` → after the role instructions, `f"{format_initiative(initiative)}\n\n"`, then the unchanged recommendation/risk/portfolio lines.
- `strategist.py::_prompt` → after the synthesis instructions, `f"{format_initiative(initiative)}\n\n"`, then the unchanged reports/debate/lessons/critique lines.
- `reflection.py::_prompt` → after the role instructions, `f"{format_initiative(decision.initiative)}\n\n"`, then the unchanged recommendation/outcome lines. (Note: reflection's source is `decision.initiative`, not a bare `initiative`.)

- [ ] **Step 7: Run the per-node and graph suites to verify behavior is preserved**

Run: `uv run pytest tests/test_analysts.py tests/test_analyst_helper.py tests/test_debate.py tests/test_risk.py tests/test_judge.py tests/test_governance.py tests/test_strategist.py tests/test_reflection.py tests/test_runner.py tests/test_graph.py -v`
Expected: PASS. These nodes are driven by `FakeChatModel` keyed on schema, so identical prompt text is not required for them to pass — but the suite proves the refactor did not break call sites, imports, or wiring.

- [ ] **Step 8: Run the full suite to confirm coverage holds**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%.

- [ ] **Step 9: Commit**

```bash
git add src/productagents/agents/_format.py src/productagents/agents/*.py tests/test_format.py
git commit -m "refactor: share format_initiative across all prompt builders"
```

---

## Task 4: Shared `format_recommendation` prompt formatter

`risk.py`, `judge.py`, and `governance.py` each hand-format the strategist's `Recommendation` into prompt text, in three slightly different shapes. Unify on one canonical block in `_format.py`. **This is the one intentional behavior change in the plan:** risk gains a `Confidence:` line it lacked, judge's confidence switches from a raw float to a `%`, and governance moves to the canonical multi-line shape. No test asserts these prompt strings (the nodes use `FakeChatModel` keyed by schema), so the suite stays green; the change is a deliberate standardization, recorded here.

**Files:**
- Modify: `src/productagents/agents/_format.py`
- Modify: `src/productagents/agents/risk.py`, `judge.py`, `governance.py`
- Test: `tests/test_format.py`

**Interfaces:**
- Produces: `_format.format_recommendation(recommendation: Recommendation | None) -> str` — returns `"(no recommendation)"` for `None`, else the canonical four-line block.
- Consumes: `schemas.Recommendation` (`.recommendation`, `.confidence`, `.rationale`, `.expected_outcomes`).

- [ ] **Step 1: Write the failing tests for `format_recommendation`**

Add to `tests/test_format.py`:

```python
from productagents.agents._format import format_recommendation
from productagents.schemas import Recommendation


def test_format_recommendation_renders_canonical_block():
    rec = Recommendation(
        recommendation="Build SSO",
        confidence=0.8,
        rationale="Strong demand",
        expected_outcomes=["unblock deals"],
    )
    assert format_recommendation(rec) == (
        "Recommendation: Build SSO\n"
        "Confidence: 80%\n"
        "Rationale: Strong demand\n"
        "Expected outcomes: ['unblock deals']"
    )


def test_format_recommendation_handles_none():
    assert format_recommendation(None) == "(no recommendation)"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_format.py -k format_recommendation -v`
Expected: FAIL with `ImportError: cannot import name 'format_recommendation'`.

- [ ] **Step 3: Implement `format_recommendation` in `_format.py`**

Update the `_format.py` schema import to include `Recommendation`:

```python
from productagents.schemas import AnalystReport, DebateTurn, Initiative, Recommendation
```

Add the function (below `format_initiative`):

```python
def format_recommendation(recommendation: Recommendation | None) -> str:
    """Render the strategist's recommendation as a prompt block.

    The canonical shape shared by the risk, judge, and governance prompts.
    """
    if recommendation is None:
        return "(no recommendation)"
    return (
        f"Recommendation: {recommendation.recommendation}\n"
        f"Confidence: {recommendation.confidence:.0%}\n"
        f"Rationale: {recommendation.rationale}\n"
        f"Expected outcomes: {recommendation.expected_outcomes}"
    )
```

- [ ] **Step 4: Run them to verify they pass**

Run: `uv run pytest tests/test_format.py -k format_recommendation -v`
Expected: PASS (both new tests green).

- [ ] **Step 5: Apply `format_recommendation` in `risk.py`**

In `risk.py`, add `format_recommendation` to the `from productagents.agents._format import ...` line. In `_prompt`, replace the three recommendation lines

```python
        f"Recommendation: {recommendation.recommendation}\n"
        f"Rationale: {recommendation.rationale}\n"
        f"Expected outcomes: {recommendation.expected_outcomes}\n\n"
```

with

```python
        f"{format_recommendation(recommendation)}\n\n"
```

- [ ] **Step 6: Apply `format_recommendation` in `judge.py`**

In `judge.py`, add `format_recommendation` to the `from productagents.agents._format import ...` line. In `_prompt`, replace the four recommendation lines

```python
        f"Recommendation: {recommendation.recommendation}\n"
        f"Confidence: {recommendation.confidence}\n"
        f"Rationale: {recommendation.rationale}\n"
        f"Expected outcomes: {recommendation.expected_outcomes}\n\n"
```

with

```python
        f"{format_recommendation(recommendation)}\n\n"
```

- [ ] **Step 7: Apply `format_recommendation` in `governance.py` and delete its local copy**

In `governance.py`, add `from productagents.agents._format import format_recommendation` to the imports. Delete the local `_format_recommendation` function (lines 31-39). In `_prompt`, change

```python
        f"Recommendation:\n{_format_recommendation(recommendation)}\n\n"
```

to

```python
        f"Recommendation:\n{format_recommendation(recommendation)}\n\n"
```

Leave `_format_risks` and `_format_portfolio` (governance-specific) untouched.

- [ ] **Step 8: Run the affected node suites to verify wiring is intact**

Run: `uv run pytest tests/test_risk.py tests/test_judge.py tests/test_governance.py tests/test_runner.py tests/test_graph.py -v`
Expected: PASS — the `None`-recommendation branch in governance is already exercised by its degrade-path test, and the schema-keyed fakes make the prompt-text change invisible to assertions.

- [ ] **Step 9: Run the full suite to confirm coverage holds**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%.

- [ ] **Step 10: Commit**

```bash
git add src/productagents/agents/_format.py src/productagents/agents/risk.py src/productagents/agents/judge.py src/productagents/agents/governance.py tests/test_format.py
git commit -m "refactor: unify recommendation prompt block via format_recommendation"
```

---

## Task 5: Runner custom-chunk dispatch table

The `custom`-mode branch of `run_decision` is a six-way `if "turn" in chunk / elif "assessment" …` chain mapping a chunk key to an event constructor. Replace it with an ordered `(key, builder)` table so adding a stage's event becomes a one-line table entry — matching the documented "Adding a stage" workflow.

**Files:**
- Modify: `src/productagents/runner.py:156-201`
- Test: `tests/test_runner.py` (existing — regression net)

**Interfaces:**
- Consumes: the `custom` chunk dicts emitted by nodes via `get_writer()` — keyed by `turn` / `assessment` / `final_verdict` / `judgment` / `verdict` / `error`, else a progress `status`.
- Produces: unchanged event stream (`DebateTurnEvent`, `RiskAssessmentEvent`, `FinalVerdictEvent`, `JudgmentEvent`, `GovernanceVerdictEvent`, `NodeErrorEvent`, `ProgressEvent`) in the same order.

- [ ] **Step 1: Confirm the existing runner test is the regression net**

Run: `uv run pytest tests/test_runner.py -v`
Expected: PASS. `test_run_decision_emits_all_event_types` already asserts every custom event type and its ordering; it is the contract this refactor must hold. (No new test needed — behavior is unchanged.)

- [ ] **Step 2: Add module-level builder functions in `runner.py`**

Add these just above `run_decision` (after the dataclass definitions). Each maps a chunk dict to its event:

```python
def _build_debate_turn(chunk: dict) -> DebateTurnEvent:
    turn = chunk["turn"]
    return DebateTurnEvent(
        round=turn["round"], side=turn["side"], argument=turn["argument"]
    )


def _build_risk_assessment(chunk: dict) -> RiskAssessmentEvent:
    a = chunk["assessment"]
    return RiskAssessmentEvent(
        reviewer=a["reviewer"], role=a["role"], level=a["level"], rationale=a["rationale"]
    )


def _build_final_verdict(chunk: dict) -> FinalVerdictEvent:
    fv = chunk["final_verdict"]
    return FinalVerdictEvent(
        verdict=fv["verdict"], rationale=fv["rationale"], decided_by=fv["decided_by"]
    )


def _build_judgment(chunk: dict) -> JudgmentEvent:
    j = chunk["judgment"]
    return JudgmentEvent(
        evidence_grounding_score=j["evidence_grounding_score"],
        rationale_coherence_score=j["rationale_coherence_score"],
        passed=j["passed"],
        critique=j["critique"],
        attempt=j["attempt"],
    )


def _build_governance_verdict(chunk: dict) -> GovernanceVerdictEvent:
    v = chunk["verdict"]
    return GovernanceVerdictEvent(verdict=v["verdict"], rationale=v["rationale"])


# Ordered so the first matching key wins, mirroring the original elif chain.
_CUSTOM_BUILDERS = (
    ("turn", _build_debate_turn),
    ("assessment", _build_risk_assessment),
    ("final_verdict", _build_final_verdict),
    ("judgment", _build_judgment),
    ("verdict", _build_governance_verdict),
)
```

- [ ] **Step 3: Replace the `if mode == "custom"` body with table lookup**

In `run_decision`, replace the entire `custom` branch (currently lines 156-201, from `if mode == "custom":` down to the `else: yield ProgressEvent(...)`) with:

```python
            if mode == "custom":
                for key, builder in _CUSTOM_BUILDERS:
                    if key in chunk:
                        yield builder(chunk)
                        break
                else:
                    if "error" in chunk:
                        yield NodeErrorEvent(
                            node=chunk.get("node", ""), message=chunk["error"]
                        )
                    else:
                        yield ProgressEvent(
                            node=chunk.get("node", ""), message=chunk.get("status", "")
                        )
```

Leave the `elif mode == "updates":` block below it untouched.

- [ ] **Step 4: Run the runner suite to verify identical event stream**

Run: `uv run pytest tests/test_runner.py -v`
Expected: PASS — same events, same order, including the error and progress fall-through cases.

- [ ] **Step 5: Run the full suite to confirm coverage holds**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%.

- [ ] **Step 6: Commit**

```bash
git add src/productagents/runner.py
git commit -m "refactor: drive runner custom-chunk events from a dispatch table"
```

---

## Task 6: TUI `_run` handler dispatch + reset extraction

`tui/app.py::_run` is a ~100-line `isinstance` chain that also accumulates local variables only `FinishedEvent` actually populates. And `on_input_submitted` carries a verbose inline panel-reset block. Extract per-event handler methods dispatched by a `{type: handler}` map, read the final record straight off the captured `FinishedEvent`, and pull the reset into `_reset_panels()`. Headless TUI tests (`tests/test_tui.py`) are the regression net.

**Files:**
- Modify: `src/productagents/tui/app.py` (`on_input_submitted` reset block ~247-265; `_run` ~283-397)
- Test: `tests/test_tui.py` (existing — regression net)

**Interfaces:**
- Consumes: the runner event dataclasses (`ProgressEvent`, `NodeCompleteEvent`, `NodeErrorEvent`, `DebateTurnEvent`, `RiskAssessmentEvent`, `JudgmentEvent`, `GovernanceVerdictEvent`, `FinalVerdictEvent`, `RecallEvent`, `FinishedEvent`).
- Produces: unchanged panel updates and an unchanged `DecisionRecord` persisted via `self._recorder` on a successful run. No new public methods on `ProductAgentsApp`; new helpers are private (`_reset_panels`, `_on_*`).

- [ ] **Step 1: Confirm the TUI suite is the regression net**

Run: `uv run pytest tests/test_tui.py -v`
Expected: PASS. These tests drive the app headless and assert panel text for every event type plus record persistence — the contract this refactor must hold. (No new test needed; behavior is unchanged.)

- [ ] **Step 2: Extract `_reset_panels()` and call it from `on_input_submitted`**

Add this method to `ProductAgentsApp` (e.g. just below `on_input_submitted`):

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

In `on_input_submitted`, replace the inline reset block (everything from `for node_id in _PANELS:` through the `self._set_state(widget_id, "idle")` loop, currently ~lines 247-265) with a single call, keeping the evidence-provenance render that precedes it:

```python
        prov = "\n".join(f"• {ref.field} ← {ref.source}" for ref in evidence.sources)
        self.query_one("#evidence-provenance", Static).update(prov or "(default)")
        self._reset_panels()
        self._run(Initiative(title=title, description=title), evidence)
```

- [ ] **Step 3: Run the TUI suite to verify the reset extraction is behavior-preserving**

Run: `uv run pytest tests/test_tui.py -v`
Expected: PASS — a decision run still clears and repopulates every panel exactly as before.

- [ ] **Step 4: Add per-event handler methods**

Add these methods to `ProductAgentsApp` (group them near `_render_recommendation`). Each is the body of one current `isinstance` branch, verbatim:

```python
    def _on_progress(self, event) -> None:
        if event.node in _PANELS:
            self.query_one(f"#{event.node}", Static).update(f"… {event.message}")
            self._set_state(event.node, "running")

    def _on_node_complete(self, event) -> None:
        if event.node not in _PANELS:
            return
        report = event.report
        if report.failed:
            self.query_one(f"#{event.node}", Static).update(
                "[red]failed — see Status / Errors below[/red]"
            )
            self._set_state(event.node, "failed")
        else:
            body = "\n".join(f"• {f}" for f in report.findings) or "(no findings)"
            self.query_one(f"#{event.node}", Static).update(body)
            self._set_state(event.node, "done")

    def _on_node_error(self, event) -> None:
        label = _TITLES.get(
            _WIDGET_FOR_NODE.get(event.node, event.node), event.node
        )
        self._log_status(f"{label}: {event.message}", level="error")
        self._mark_failed(event.node)

    def _on_debate_turn(self, event) -> None:
        self._debate_lines.append(
            f"[{event.side} · round {event.round}] {event.argument}"
        )
        self.query_one("#debate", Static).update("\n\n".join(self._debate_lines))

    def _on_risk_assessment(self, event) -> None:
        self._risk_lines.append(f"[{event.role} · {event.level}] {event.rationale}")
        self.query_one("#risk", Static).update("\n\n".join(self._risk_lines))

    def _on_judgment(self, event) -> None:
        status = "PASS" if event.passed else "FAIL"
        self.query_one("#judgment", Static).update(
            f"[b]{status}[/b] (attempt {event.attempt})\n\n"
            f"Evidence: {event.evidence_grounding_score:.0%}  "
            f"Coherence: {event.rationale_coherence_score:.0%}\n\n"
            f"{event.critique}"
        )
        self._set_state("judgment", "done" if event.passed else "failed")

    def _on_governance_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            f"[b]{event.verdict}[/b]\n\n{event.rationale}"
        )

    def _on_final_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            f"[b]FINAL ({event.decided_by}): {event.verdict}[/b]\n\n{event.rationale}"
        )

    def _on_recall(self, event) -> None:
        body = "\n".join(f"• {line}" for line in event.lessons) or (
            "(no relevant past lessons)"
        )
        self.query_one("#recall", Static).update(body)
        self._set_state("recall", "done")

    def _on_finished(self, event) -> None:
        self._render_recommendation(event.recommendation)
        self._set_state("strategist", "done")
```

- [ ] **Step 5: Rewrite `_run` to dispatch through the handler map**

Replace the body of `_run` (the worker, currently ~lines 283-397) with the dispatch version. The accumulation locals are gone; the terminal `DecisionRecord` is built straight from the captured `FinishedEvent`:

```python
    @work(exclusive=True)
    async def _run(self, initiative: Initiative, evidence) -> None:
        if self._runner is None:
            return
        handlers = {
            ProgressEvent: self._on_progress,
            NodeCompleteEvent: self._on_node_complete,
            NodeErrorEvent: self._on_node_error,
            DebateTurnEvent: self._on_debate_turn,
            RiskAssessmentEvent: self._on_risk_assessment,
            JudgmentEvent: self._on_judgment,
            GovernanceVerdictEvent: self._on_governance_verdict,
            FinalVerdictEvent: self._on_final_verdict,
            RecallEvent: self._on_recall,
            FinishedEvent: self._on_finished,
        }
        finished: FinishedEvent | None = None
        portfolio = self._reader()
        outcomes = self._outcome_reader()
        try:
            async for event in self._runner(
                initiative,
                evidence,
                portfolio=portfolio,
                outcomes=outcomes,
                approver=self._ask_human,
            ):
                handler = handlers.get(type(event))
                if handler is not None:
                    handler(event)
                if isinstance(event, FinishedEvent):
                    finished = event
        except Exception as exc:  # noqa: BLE001 - never crash the worker
            self._log_status(f"run failed: {exc}", level="error")
            return

        if finished is not None and finished.recommendation is not None:
            self._recorder(
                DecisionRecord(
                    initiative=initiative,
                    recommendation=finished.recommendation,
                    reports=finished.reports,
                    debate=finished.debate,
                    risks=finished.risks,
                    governance=finished.governance,
                    judgment=finished.judgment,
                    prior_lessons=finished.prior_lessons,
                    evidence_sources=evidence.sources,
                    timestamp=datetime.now(UTC).isoformat(),
                )
            )
```

- [ ] **Step 6: Run the TUI suite to verify behavior is preserved**

Run: `uv run pytest tests/test_tui.py tests/test_approval_tui.py tests/test_reflection_tui.py -v`
Expected: PASS — every panel renders identically, the HITL approval flow still resumes, and `DecisionRecord` is persisted with the same fields (including `judgment` and `evidence_sources`).

- [ ] **Step 7: Run the full suite to confirm coverage holds**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%.

- [ ] **Step 8: Refresh the knowledge graph**

Run: `graphify update .`
Expected: completes (AST-only, no API cost).

- [ ] **Step 9: Commit**

```bash
git add src/productagents/tui/app.py
git commit -m "refactor: dispatch TUI run events via a handler map; extract _reset_panels"
```

---

## Self-Review

**1. Spec coverage** — the user selected four refactor areas; each maps to a task (or task pair):
- Env-var config helpers → **Task 1**.
- JSONL persistence dedup → **Task 2**.
- Shared prompt formatters → **Task 3** (`format_initiative`) + **Task 4** (`format_recommendation`).
- Event dispatch + TUI `_run` → **Task 5** (runner table) + **Task 6** (TUI handlers + reset).
No gaps.

**2. Placeholder scan** — every code step shows complete, paste-ready code; every run step shows the exact command and expected PASS/FAIL. No "TBD"/"add error handling"/"similar to Task N" placeholders.

**3. Type consistency** — names are consistent across tasks: `env_int`/`env_float` (Task 1) are the same symbols imported in `debate.py`/`judge.py`; `_read_jsonl`/`_append_jsonl`/`_path(path, default)` (Task 2) match their call sites; `format_initiative`/`format_recommendation` (Tasks 3-4) match the imports added to each agent; `_CUSTOM_BUILDERS` entries (Task 5) return the exact event types `run_decision` already yields; the `handlers` map keys (Task 6) are the runner event classes already imported at the top of `tui/app.py`, and the `_on_*` methods match the map values. The `DecisionRecord` fields read off `finished` in Task 6 match `schemas.DecisionRecord` (`initiative`, `recommendation`, `reports`, `debate`, `risks`, `governance`, `judgment`, `prior_lessons`, `evidence_sources`, `timestamp`).

**Notes for the implementer:**
- Tasks are independent and may be done in any order, but the listed order minimizes import churn. Each ends green and is independently reviewable.
- After removing `import os` in Task 1 (debate/judge) and deleting the local `_format_recommendation` in Task 4 (governance), run `uv run ruff check .` (the repo's linter, also in pre-commit) to catch any now-unused import the edits left behind.
- The only intentional behavior change in the whole plan is the Task 4 prompt-text unification — flagged in that task. Everything else is byte-identical output, guarded by the existing suite.
