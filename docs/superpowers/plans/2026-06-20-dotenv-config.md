# Dotenv Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users put `PRODUCTAGENTS_*` and provider API keys in a `.env` file (auto-loaded at startup) instead of `export`-ing them, and ship a `.env.example` template.

**Architecture:** Add `python-dotenv` as a runtime dependency. Add a thin `productagents.config.load_env()` wrapper over `load_dotenv(override=False)` and call it as the very first line of the `productagents` entry point (`tui/app.py::main`). Because every consumer (`llm.get_model`, `debate.get_debate_rounds`, `app.py`) reads `os.environ` *lazily* at call time, loading `.env` once before `_build_app()` runs makes the values visible everywhere with no other code changes. `override=False` means a genuinely exported shell variable always wins over `.env`, and tests (which never call `main()`) stay fully offline and unaffected.

**Tech Stack:** Python ≥ 3.14, uv, python-dotenv ≥ 1.0, pytest (`asyncio_mode = "auto"`).

## Global Constraints

- Python `>=3.14` (from `pyproject.toml` `requires-python`).
- Dependency manager is **uv** — add deps with `uv add`, run things with `uv run`.
- Coverage gate is enforced: `pytest` runs with `--cov-fail-under=90`. New code must be covered.
- Lint/format with ruff; the curated rule set in `[tool.ruff.lint]` includes `BLE` (blind-except) — do **not** add bare/blind `except` without a `# noqa: BLE001`.
- `.env` is **already** in `.gitignore` (under the `# Environments` section). Do not commit a real `.env`. `.env.example` is committed and must contain **no real secrets** — placeholders only.
- Import name is `from dotenv import load_dotenv`; PyPI/package name is `python-dotenv`.
- `load_dotenv` signature (verified against python-dotenv v1.x docs): `load_dotenv(dotenv_path=None, stream=None, verbose=False, override=False, interpolate=True, encoding="utf-8") -> bool`. With `dotenv_path=None` it auto-discovers via `find_dotenv()` (walks up from the cwd). Returns `True` if a file was loaded.

---

### Task 1: `config.load_env()` helper + dependency

**Files:**
- Modify: `pyproject.toml` (add `python-dotenv>=1.0` to `[project].dependencies`)
- Create: `src/productagents/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing (new leaf module).
- Produces: `productagents.config.load_env(dotenv_path: str | os.PathLike[str] | None = None) -> bool` — wraps `dotenv.load_dotenv` with `override=False`; returns whether a `.env` file was loaded. With the default `dotenv_path=None`, auto-discovers the nearest `.env` by walking up from the current working directory.

- [ ] **Step 1: Add the dependency**

Run:
```bash
uv add "python-dotenv>=1.0"
```
Expected: `pyproject.toml` `[project].dependencies` now lists `python-dotenv>=1.0`; `uv.lock` updates; command exits 0.

- [ ] **Step 2: Write the failing test**

Create `tests/test_config.py`:
```python
"""Tests for the dotenv-backed configuration loader."""

from productagents.config import load_env


def test_load_env_populates_missing_var_from_file(tmp_path, monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_TEST_VAR", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("PRODUCTAGENTS_TEST_VAR=from_file\n")

    loaded = load_env(env_file)

    assert loaded is True
    import os

    assert os.environ["PRODUCTAGENTS_TEST_VAR"] == "from_file"


def test_load_env_does_not_override_existing_var(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_TEST_VAR", "from_shell")
    env_file = tmp_path / ".env"
    env_file.write_text("PRODUCTAGENTS_TEST_VAR=from_file\n")

    load_env(env_file)

    import os

    assert os.environ["PRODUCTAGENTS_TEST_VAR"] == "from_shell"


def test_load_env_returns_false_when_no_file(tmp_path):
    missing = tmp_path / "nope.env"

    assert load_env(missing) is False
```

> Note: `monkeypatch.setenv`/`delenv` auto-restore `os.environ` after each test, so the first test's write to `os.environ` is cleaned up automatically (it patches the same `PRODUCTAGENTS_TEST_VAR` key).

- [ ] **Step 3: Run the test to verify it fails**

Run:
```bash
uv run pytest tests/test_config.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'productagents.config'` (collection error).

- [ ] **Step 4: Write the minimal implementation**

Create `src/productagents/config.py`:
```python
"""Startup configuration loading.

Loads environment variables from a `.env` file so users don't have to
`export` `PRODUCTAGENTS_*` settings and provider API keys by hand. Called
once at the `productagents` entry point, before any node reads `os.environ`.
"""

import os

from dotenv import load_dotenv


def load_env(dotenv_path: str | os.PathLike[str] | None = None) -> bool:
    """Load variables from a `.env` file into the process environment.

    With the default `dotenv_path=None`, the nearest `.env` is discovered by
    walking up from the current working directory. Existing environment
    variables are never overwritten (`override=False`), so a value exported in
    the shell always wins over the file. Returns `True` if a file was loaded.
    """
    return load_dotenv(dotenv_path=dotenv_path, override=False)
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
uv run pytest tests/test_config.py -v
```
Expected: PASS (3 passed).

- [ ] **Step 6: Lint**

Run:
```bash
uv run ruff check src/productagents/config.py tests/test_config.py && uv run ruff format --check src/productagents/config.py tests/test_config.py
```
Expected: no errors. (If format check fails, run `uv run ruff format src/productagents/config.py tests/test_config.py` and re-run.)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/productagents/config.py tests/test_config.py
git commit -m "feat: add dotenv-backed config loader"
```

---

### Task 2: Load `.env` at the `main()` entry point

**Files:**
- Modify: `src/productagents/tui/app.py` (import `load_env`; call it first in `main()`)
- Test: `tests/test_app_main.py`

**Interfaces:**
- Consumes: `productagents.config.load_env` (from Task 1).
- Produces: `main()` calls `load_env()` (no args → auto-discovery) before constructing the app, so env values from `.env` are visible to `get_model()`/`get_debate_rounds()`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_app_main.py`:
```python
"""Tests for the productagents entry point wiring."""

import pytest

from productagents.tui import app as app_module


def test_main_loads_env_before_building_app(monkeypatch):
    calls = []

    def fake_load_env():
        calls.append("load_env")
        return True

    def fake_build_app():
        calls.append("build_app")
        raise RuntimeError("stop before app.run()")

    monkeypatch.setattr(app_module, "load_env", fake_load_env)
    monkeypatch.setattr(app_module, "_build_app", fake_build_app)

    with pytest.raises(SystemExit):
        app_module.main()

    assert calls == ["load_env", "build_app"]
```

> Why this shape: `main()` wraps `_build_app()` in `try/except Exception` and re-raises as `SystemExit`. Forcing `_build_app` to raise lets us assert ordering without ever reaching `app.run()` (which would launch the TUI). `calls == ["load_env", "build_app"]` proves `load_env` ran first.

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
uv run pytest tests/test_app_main.py -v
```
Expected: FAIL with `AttributeError: <module 'productagents.tui.app'> does not have the attribute 'load_env'` (raised by `monkeypatch.setattr`).

- [ ] **Step 3: Add the import**

In `src/productagents/tui/app.py`, add the import alongside the other first-party imports. Place it immediately after the `from productagents.agents.reflection import reflect` line:
```python
from productagents.agents.reflection import reflect
from productagents.config import load_env
from productagents.evidence import EvidenceError, collect_evidence, load_scenario
```

> Keep imports sorted (ruff `I`): `productagents.agents.reflection` → `productagents.config` → `productagents.evidence` is alphabetical. Run the lint step below to confirm.

- [ ] **Step 4: Call `load_env()` first in `main()`**

In `src/productagents/tui/app.py`, change the start of `main()` from:
```python
def main() -> None:
    try:
        app = _build_app()
```
to:
```python
def main() -> None:
    load_env()
    try:
        app = _build_app()
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
uv run pytest tests/test_app_main.py -v
```
Expected: PASS (1 passed).

- [ ] **Step 6: Lint**

Run:
```bash
uv run ruff check src/productagents/tui/app.py tests/test_app_main.py && uv run ruff format --check src/productagents/tui/app.py tests/test_app_main.py
```
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add src/productagents/tui/app.py tests/test_app_main.py
git commit -m "feat: load .env at the productagents entry point"
```

---

### Task 3: Ship `.env.example`

**Files:**
- Create: `.env.example`
- Test: `tests/test_env_example.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a committed `.env.example` documenting every supported variable. The test guards that it stays in sync with the variable names the code actually reads and that it contains no real secret.

- [ ] **Step 1: Write the failing test**

Create `tests/test_env_example.py`:
```python
"""Guard that .env.example documents every supported variable."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"

EXPECTED_KEYS = (
    "PRODUCTAGENTS_MODEL",
    "PRODUCTAGENTS_MODEL_PROVIDER",
    "PRODUCTAGENTS_DEBATE_ROUNDS",
    "ANTHROPIC_API_KEY",
)


def test_env_example_exists():
    assert ENV_EXAMPLE.is_file()


def test_env_example_documents_all_keys():
    text = ENV_EXAMPLE.read_text()
    for key in EXPECTED_KEYS:
        assert key in text, f"{key} missing from .env.example"


def test_env_example_has_no_real_anthropic_key():
    text = ENV_EXAMPLE.read_text()
    # A real Anthropic key starts with "sk-ant-"; the template must not embed one.
    assert "sk-ant-" not in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
uv run pytest tests/test_env_example.py -v
```
Expected: FAIL — `test_env_example_exists` fails because `.env.example` does not yet exist.

- [ ] **Step 3: Create `.env.example`**

Use placeholders that do **not** contain the literal `sk-ant-` (the guard test in Step 1 rejects that substring, since it marks a real Anthropic key). Create `.env.example` with exactly this content:
```bash
# ProductAgents configuration.
# Copy this file to `.env` (which is git-ignored) and fill in your values.
# Variables already exported in your shell take precedence over this file.

# --- Model selection (provider-agnostic) ---
# Provider-prefixed model id. Default: anthropic:claude-sonnet-4-6
PRODUCTAGENTS_MODEL="anthropic:claude-sonnet-4-6"

# Only needed for providers that are not LangChain-native (then set the
# matching API key below). Leave blank/commented for Anthropic.
# PRODUCTAGENTS_MODEL_PROVIDER="openai"

# --- Provider API key (set the one matching your model) ---
ANTHROPIC_API_KEY="your-anthropic-api-key"
# OPENAI_API_KEY="your-openai-api-key"

# --- Debate tuning ---
# Number of debate rounds (one advocate argument + one skeptic rebuttal each).
# Default: 2
PRODUCTAGENTS_DEBATE_ROUNDS="2"
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
uv run pytest tests/test_env_example.py -v
```
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add .env.example tests/test_env_example.py
git commit -m "docs: add .env.example configuration template"
```

---

### Task 4: Document `.env` usage in the README

**Files:**
- Modify: `README.md` (the `### Configure a model` section, around lines 487-509)

**Interfaces:**
- Consumes: nothing.
- Produces: README tells users to copy `.env.example` to `.env` as the recommended path, keeping `export` as the alternative.

- [ ] **Step 1: Add the `.env` instructions**

In `README.md`, locate the `### Configure a model` section. Immediately after the section heading and its intro sentence, before the first `export PRODUCTAGENTS_MODEL=...` block, insert:

```markdown
The easiest way is to copy the template and edit it — `.env` is loaded
automatically on startup and is git-ignored:

```bash
cp .env.example .env
# then edit .env and set your provider API key
```

Any variable already exported in your shell takes precedence over `.env`.
You can still configure everything with plain `export`s instead:
```

> The triple-backtick `bash` block inside the inserted markdown must be closed with its own triple backticks (as shown). Verify the surrounding fences still balance after editing — render/preview the section or run `grep -c '^```' README.md` and confirm the count is even.

- [ ] **Step 2: Verify the docs read correctly**

Run:
```bash
grep -n "cp .env.example .env" README.md
```
Expected: one match inside the `### Configure a model` section.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document .env-based configuration"
```

---

### Task 5: Full-suite verification

**Files:** none (verification only).

- [ ] **Step 1: Run the full test suite with coverage**

Run:
```bash
uv run pytest
```
Expected: all tests pass (the prior suite plus the new `test_config.py`, `test_app_main.py`, `test_env_example.py`); coverage stays ≥ 90% (`--cov-fail-under=90` does not trip).

- [ ] **Step 2: Lint and format the whole tree**

Run:
```bash
uv run ruff check . && uv run ruff format --check .
```
Expected: no errors.

- [ ] **Step 3: Smoke-test `.env` loading manually (optional but recommended)**

Create a throwaway `.env` with a recognizable debate-round value and confirm it is picked up without exporting:
```bash
printf 'PRODUCTAGENTS_DEBATE_ROUNDS=3\n' > .env
uv run python -c "from productagents.config import load_env; load_env(); from productagents.agents.debate import get_debate_rounds; print(get_debate_rounds())"
```
Expected: prints `3`. Then remove the throwaway file:
```bash
rm .env
```

- [ ] **Step 4: Confirm `.env` is not tracked by git**

Run:
```bash
git status --porcelain | grep -E '(^|\s)\.env$' || echo "clean: .env not tracked"
```
Expected: prints `clean: .env not tracked` (the `.gitignore` `# Environments` rule already covers `.env`).
