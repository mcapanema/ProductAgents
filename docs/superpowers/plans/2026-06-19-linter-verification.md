# Linter Verification Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen static verification by replacing ruff's near-empty default ruleset with an explicit curated set, adding the `ty` type checker, and enforcing both locally (pre-commit) and in CI.

**Architecture:** Four self-contained tasks: (1) expand ruff lint rules in `pyproject.toml` and auto-fix the resulting findings; (2) add `ty` as a pinned dev dependency with one targeted suppression; (3) add a `.pre-commit-config.yaml` so ruff + ty run before every commit; (4) add a `ty` gate to the existing CI workflow. Each task ends green and is independently reviewable.

**Tech Stack:** Python ≥ 3.14, `uv`, `ruff` 0.15.18, `ty` 0.0.51, `pre-commit`, GitHub Actions.

## Global Constraints

- Python version floor: `>=3.14` (already in `pyproject.toml`; do not change).
- Package manager is `uv` only. Never invoke `pip`/`conda`. Use `uv add --dev <pkg>` to add dev deps (updates both `pyproject.toml` and `uv.lock`).
- Pin pre-1.0 tools exactly: `ty==0.0.51`. The ruff-pre-commit `rev` must match the installed ruff: `v0.15.18`.
- Line length is `88` (already set; do not change).
- **Do NOT enable ruff's `TC` (flake8-type-checking) rules.** Moving Pydantic field-type imports into `if TYPE_CHECKING:` blocks breaks Pydantic's runtime annotation evaluation. This codebase is Pydantic-heavy (`schemas.py`).
- Tests must remain fully offline (no API key); none of this work touches test execution.
- CI parity: every gate enforced locally (pre-commit) must also run in CI, and vice versa, so a green local commit predicts a green CI run.

---

## File Structure

| File | Responsibility | Change |
| --- | --- | --- |
| `pyproject.toml` | Tool config + deps. Holds the new `[tool.ruff.lint]` ruleset and the `ty`/`pre-commit` dev deps. | Modify |
| `uv.lock` | Locked dependency graph. Updated automatically by `uv add --dev`. | Modify (auto) |
| `src/productagents/tui/app.py` | TUI entrypoint. Receives ruff auto-fixes (UP017, UP037, dead noqa removal). | Modify (auto) |
| `tests/test_tui.py` | Receives ruff import-sort auto-fix (I001). | Modify (auto) |
| `src/productagents/graph.py` | LangGraph assembly. Gets one targeted `# ty: ignore` for a langgraph stub limitation. | Modify |
| `.pre-commit-config.yaml` | Local pre-commit hooks for ruff + ty. | Create |
| `.github/workflows/ci.yml` | CI pipeline. Gains a `ty` type-check step. | Modify |

---

### Task 1: Expand the ruff lint ruleset

Ruff currently runs only its default rules (`E4`, `E7`, `E9`, `F`) because `[tool.ruff]` sets nothing beyond `line-length`. The codebase already carries `# noqa: BLE001` suppressions for a rule (`flake8-blind-except`) that isn't even enabled — clear evidence a broader ruleset was intended. This task makes the ruleset explicit. All resulting findings are auto-fixable; no manual code edits are required.

**Files:**
- Modify: `pyproject.toml` (the `[tool.ruff]` section, near end of file)
- Modify (auto-fix): `src/productagents/tui/app.py`, `tests/test_tui.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a `[tool.ruff.lint]` table whose `select` list is the canonical ruleset relied on by Task 3 (pre-commit) and the existing CI lint step. Selected codes: `E, F, W, I, UP, B, C4, SIM, BLE, RUF, PT`.

- [ ] **Step 1: Observe the current (too-narrow) ruleset passes trivially**

Run: `uv run ruff check .`
Expected: `All checks passed!` — because the default ruleset is nearly empty. This is the weakness we are fixing.

- [ ] **Step 2: See what a broader ruleset would catch (the "failing" state)**

Run: `uv run ruff check --select "E,F,W,I,UP,B,C4,SIM,BLE,RUF,PT" .`
Expected: `Found 4 errors.` — one `UP017` and one `UP037` and one unused `RUF100` noqa in `src/productagents/tui/app.py`, and one `I001` unsorted import in `tests/test_tui.py`. All marked `[*]` (fixable).

- [ ] **Step 3: Make the ruleset explicit in `pyproject.toml`**

Replace the existing `[tool.ruff]` section at the end of `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
# target-version is inferred from project.requires-python (>=3.14).

[tool.ruff.lint]
# Curated, explicit rule set. The default ruff selection is nearly empty;
# this locks in the rules the codebase was already written against (note the
# existing `# noqa: BLE001` suppressions).
#
# `TC` (flake8-type-checking) is intentionally EXCLUDED: moving Pydantic
# field-type imports into `if TYPE_CHECKING:` blocks breaks Pydantic's
# runtime annotation evaluation (see schemas.py).
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "W",   # pycodestyle warnings
    "I",   # isort (import sorting)
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
    "BLE", # flake8-blind-except (makes the existing `# noqa: BLE001` meaningful)
    "RUF", # ruff-specific rules
    "PT",  # flake8-pytest-style
]
```

- [ ] **Step 4: Auto-fix the findings, then re-format**

Run: `uv run ruff check --fix . && uv run ruff format .`
Expected: ruff reports `Fixed 4 errors` (datetime.UTC alias in `app.py`, removed quotes from the `_build_app` return annotation, removed the now-redundant `BLE001` noqa in `main()` whose blind-except is satisfied by using `exc`, and sorted imports in `test_tui.py`), and format reports the files left unchanged or reformatted. The four `# noqa: BLE001` comments in `agents/*.py` remain — there `BLE001` genuinely fires, so they are still needed.

- [ ] **Step 5: Verify the project is clean under the new ruleset**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: `All checks passed!` followed by `N files already formatted`.

- [ ] **Step 6: Confirm the test suite still passes**

Run: `uv run pytest`
Expected: full suite passes (coverage gate `--cov-fail-under=90` satisfied). The auto-fixes are behavior-preserving (`datetime.now(UTC)` ≡ `datetime.now(timezone.utc)`).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/productagents/tui/app.py tests/test_tui.py
git commit -m "lint: enable explicit ruff ruleset and auto-fix findings"
```

---

### Task 2: Add the `ty` type checker as a local gate

The codebase is densely annotated (28 of 32 functions carry return types) but no type checker runs. `ty` (astral's checker) resolves the project's third-party imports from `.venv` with zero config and finds exactly one diagnostic — a langgraph stub limitation, not a real bug — which we suppress narrowly.

**Files:**
- Modify: `pyproject.toml` (`[dependency-groups]` → `dev`) and `uv.lock` (auto)
- Modify: `src/productagents/graph.py:32`

**Interfaces:**
- Consumes: nothing.
- Produces: `uv run ty check src` as a passing command, relied on by Task 3 (pre-commit) and Task 4 (CI).

- [ ] **Step 1: Add `ty` as a pinned dev dependency**

Run: `uv add --dev "ty==0.0.51"`
Expected: `pyproject.toml`'s `dev` group gains `"ty==0.0.51"` and `uv.lock` updates. Command exits 0.

- [ ] **Step 2: Observe the single type-check failure**

Run: `uv run ty check src`
Expected: `Found 1 diagnostic` — `error[invalid-argument-type]` at `src/productagents/graph.py:32`, reporting that `GraphState` does not satisfy langgraph's `StateT` upper bound `TypedDictLikeV1 | DataclassLike`. (This is a stub-precision issue; `GraphState` is a valid `TypedDict` and works at runtime.)

- [ ] **Step 3: Add a targeted suppression in `graph.py`**

In `src/productagents/graph.py`, change the line inside `build_graph`:

```python
    graph = StateGraph(GraphState)
```

to:

```python
    # ty: GraphState is a valid TypedDict; langgraph's StateT bound stub is too
    # narrow to recognize it. Suppress narrowly rather than weakening the type.
    graph = StateGraph(GraphState)  # ty: ignore[invalid-argument-type]
```

- [ ] **Step 4: Verify `ty` is clean**

Run: `uv run ty check src`
Expected: `All checks passed!`

- [ ] **Step 5: Confirm ruff still passes (the new comment must not trip it)**

Run: `uv run ruff check src/productagents/graph.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/productagents/graph.py
git commit -m "types: add ty type checker with targeted langgraph suppression"
```

---

### Task 3: Enforce ruff + ty locally with pre-commit

Add a pre-commit configuration so the same gates run before every commit, catching issues before they reach CI.

**Files:**
- Modify: `pyproject.toml` (`[dependency-groups]` → `dev`) and `uv.lock` (auto)
- Create: `.pre-commit-config.yaml`

**Interfaces:**
- Consumes: the ruff ruleset from Task 1 and the `uv run ty check src` command from Task 2.
- Produces: a working `uv run pre-commit run --all-files` invocation.

- [ ] **Step 1: Add `pre-commit` as a dev dependency**

Run: `uv add --dev pre-commit`
Expected: `pyproject.toml`'s `dev` group gains `pre-commit` and `uv.lock` updates. Exits 0.

- [ ] **Step 2: Create the pre-commit configuration**

Create `.pre-commit-config.yaml`:

```yaml
# Local verification gates, kept in parity with .github/workflows/ci.yml.
# ruff via the official ruff-pre-commit repo (rev pinned to the installed
# ruff version); ty as a local hook so it uses the project's pinned ty.
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.18
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: ty
        name: ty type check
        entry: uv run ty check src
        language: system
        types: [python]
        pass_filenames: false
```

- [ ] **Step 3: Install the git hook**

Run: `uv run pre-commit install`
Expected: `pre-commit installed at .git/hooks/pre-commit`.

- [ ] **Step 4: Run all hooks against the whole repo**

Run: `uv run pre-commit run --all-files`
Expected: `ruff-check`, `ruff-format`, and `ty type check` each report `Passed`. (First run downloads the ruff-pre-commit environment; that is normal.)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .pre-commit-config.yaml
git commit -m "ci: add pre-commit hooks for ruff and ty"
```

---

### Task 4: Gate `ty` in CI

The CI workflow already runs `ruff check`, `ruff format --check`, and `pytest`. Add a type-check step so `ty` failures block merges too.

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the `uv run ty check src` command (Task 2) and the updated `uv.lock` (so `--frozen` resolves `ty`).
- Produces: nothing downstream.

- [ ] **Step 1: Add a "Type check" step after "Format check"**

In `.github/workflows/ci.yml`, insert the step between the `Format check` step and the `Test` step:

```yaml
      - name: Format check
        run: uv run ruff format --check .

      - name: Type check
        run: uv run --frozen ty check src

      - name: Test
        run: uv run --frozen pytest
```

- [ ] **Step 2: Locally reproduce exactly what CI will run**

Run: `uv run --frozen ty check src`
Expected: `All checks passed!` (If this reports a lock mismatch, run `uv lock` and re-commit `uv.lock` — Task 2/3 should have kept it current.)

- [ ] **Step 3: Sanity-check the workflow YAML is well-formed**

Run: `uv run python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('ci.yml OK')"`
Expected: `ci.yml OK` (no YAML parse error).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add ty type-check step to the workflow"
```

---

## Self-Review

**Spec coverage** (the chosen scope was "Ruff + pre-commit + types"):
- Ruff rule expansion → Task 1. ✅
- Pre-commit → Task 3. ✅
- Type checking → Task 2 (local) + Task 4 (CI gate). ✅
- CI parity constraint → ruff already in CI; ty added in Task 4; pre-commit mirrors both. ✅

**Placeholder scan:** No TBD/TODO/"handle edge cases" placeholders. Every code/config step shows complete content. The only auto-generated content (`uv.lock` deltas, ruff auto-fixes) is produced by exact commands with stated expected output. ✅

**Type/name consistency:** The ruleset code list `E, F, W, I, UP, B, C4, SIM, BLE, RUF, PT` is identical in Task 1 (pyproject) and is the set the Task 3 ruff-pre-commit hook enforces. The command `uv run ty check src` is identical across Tasks 2, 3, and 4. The suppression code `invalid-argument-type` matches the diagnostic ID observed in Task 2 Step 2. Ruff rev `v0.15.18` matches the installed ruff and the `ty==0.0.51` pin is consistent across tasks. ✅
