# First-Run Setup Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `productagents` launches, show a home menu (Set up / Run a decision / Quit), statically check that a model + matching API key are configured, and — when something is missing — guide the user through a setup screen that writes the values to `.env`.

**Architecture:** A new pure module `setup.py` owns the provider→key-var registry, a static `check_config()` readiness check, and a `write_env()` `.env` writer (wrapping `python-dotenv`). Two new Textual screens (`HomeScreen`, `SetupScreen`) provide the menu and the guided collection form. `ProductAgentsApp` gains a small orchestration layer: on mount it pushes the home menu and, if config is incomplete, auto-opens setup; after a successful save it rebuilds the model/graph so the new config takes effect in the same session. The decision UI stays the app's base screen and is revealed by popping the home menu.

**Tech Stack:** Python ≥ 3.14, Textual ≥ 4.0, python-dotenv ≥ 1.0, Pydantic, pytest (offline, `asyncio_mode = "auto"`).

## Global Constraints

- Python ≥ 3.14; managed with **uv** (`uv run pytest`, `uv run productagents`).
- All tests run **fully offline** — no API key, no network. Use `tests/fakes.py::FakeChatModel` and injected fakes; never construct a real model in a test.
- The readiness check is **static only** — it inspects env vars and never makes a network/LLM call.
- **Nodes/screens degrade, never crash** — wrap fallible calls in `try/except Exception` with `# noqa: BLE001` and surface the error in the UI.
- Coverage gate is **90%** (`--cov-fail-under=90`, configured in `pyproject.toml`); every new module/branch needs happy-path **and** failure/degrade coverage.
- Ruff rule set includes `BLE` (blind-except needs `# noqa: BLE001`), `I` (import sorting), `F` (unused imports). Keep imports clean.
- Existing env vars: `PRODUCTAGENTS_MODEL` (default `anthropic:claude-sonnet-4-6`), `PRODUCTAGENTS_MODEL_PROVIDER` (optional), provider key var (e.g. `ANTHROPIC_API_KEY`). `config.load_env()` loads `.env` with `override=False` (shell wins).

## File Structure

- **Create** `src/productagents/setup.py` — provider registry, `provider_for`, `api_key_var_for`, `ConfigStatus`, `check_config`, `write_env`. Pure/offline; the single source of truth for "is the app configured?" and ".env persistence".
- **Create** `src/productagents/tui/setup_screen.py` — `SetupScreen(ModalScreen[bool])`: collect model/provider/key, validate, persist via injected writer.
- **Create** `src/productagents/tui/home_screen.py` — `HomeScreen(Screen)`: landing menu; buttons delegate to app methods.
- **Modify** `src/productagents/tui/app.py` — constructor seams (`config_checker`, `env_writer`, `rebuild`, `show_home`), `on_mount` push-home, `_open_home`/`open_setup`/`_after_setup`/`start_decision`/`action_home`, resilient `_build_app`, simplified `main`.
- **Modify** `src/productagents/tui/app.tcss` — minimal styling for the two new screens.
- **Create** `tests/test_setup.py` — unit tests for the pure module.
- **Create** `tests/test_setup_tui.py` — `SetupScreen` behavior via a host app.
- **Create** `tests/test_home_tui.py` — `HomeScreen` behavior via a host app.
- **Modify** `tests/fakes.py` — add `ready_status()` helper.
- **Modify** `tests/test_tui.py` — add `show_home=False` to existing decision tests; add integration tests for the menu/setup flow.
- **Modify** `tests/test_approval_tui.py`, `tests/test_reflection_tui.py` — add `show_home=False`.
- **Modify** `tests/test_app_main.py` — replace the SystemExit-based tests with resilient-`_build_app` + ordered-`main` tests.
- **Modify** `CLAUDE.md`, `src/productagents/CLAUDE.md`, `src/productagents/tui/CLAUDE.md`, `.env.example` — document the setup flow.

---

### Task 1: Config readiness check (`setup.py` core)

**Files:**
- Create: `src/productagents/setup.py`
- Test: `tests/test_setup.py`

**Interfaces:**
- Consumes: `productagents.llm.DEFAULT_MODEL` (the `"anthropic:claude-sonnet-4-6"` default).
- Produces (relied on by Tasks 2–5):
  - `PROVIDER_API_KEYS: dict[str, str]`
  - `provider_for(model: str, explicit_provider: str | None = None) -> str`
  - `api_key_var_for(provider: str) -> str`
  - `ConfigStatus` dataclass — fields `model: str`, `provider: str`, `key_var: str`, `key_present: bool`, `problems: list[str]`; property `ok: bool`.
  - `check_config(env: Mapping[str, str] | None = None) -> ConfigStatus`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_setup.py`:

```python
"""Tests for the static config-readiness check and helpers."""

from productagents.setup import (
    ConfigStatus,
    api_key_var_for,
    check_config,
    provider_for,
)


def test_provider_for_parses_prefix():
    assert provider_for("anthropic:claude-sonnet-4-6") == "anthropic"


def test_provider_for_explicit_override_wins():
    assert provider_for("some-model", "openai") == "openai"


def test_provider_for_bare_model_is_unknown():
    assert provider_for("just-a-model") == ""


def test_api_key_var_for_known_provider():
    assert api_key_var_for("anthropic") == "ANTHROPIC_API_KEY"


def test_api_key_var_for_unknown_provider_is_derived():
    assert api_key_var_for("cohere") == "COHERE_API_KEY"


def test_api_key_var_for_empty_provider():
    assert api_key_var_for("") == ""


def test_check_config_ok_when_key_present():
    env = {
        "PRODUCTAGENTS_MODEL": "anthropic:claude-sonnet-4-6",
        "ANTHROPIC_API_KEY": "sk-test",
    }
    status = check_config(env)
    assert isinstance(status, ConfigStatus)
    assert status.ok is True
    assert status.provider == "anthropic"
    assert status.key_var == "ANTHROPIC_API_KEY"
    assert status.key_present is True
    assert status.problems == []


def test_check_config_reports_missing_key():
    env = {"PRODUCTAGENTS_MODEL": "anthropic:claude-sonnet-4-6"}
    status = check_config(env)
    assert status.ok is False
    assert status.key_present is False
    assert any("ANTHROPIC_API_KEY" in p for p in status.problems)


def test_check_config_reports_unknown_provider():
    env = {"PRODUCTAGENTS_MODEL": "mystery-model"}
    status = check_config(env)
    assert status.ok is False
    assert status.provider == ""
    assert any("provider" in p.lower() for p in status.problems)


def test_check_config_defaults_to_anthropic_when_model_unset():
    status = check_config({})
    assert status.provider == "anthropic"
    assert status.key_var == "ANTHROPIC_API_KEY"


def test_check_config_blank_key_is_not_present():
    env = {"PRODUCTAGENTS_MODEL": "anthropic:m", "ANTHROPIC_API_KEY": "   "}
    status = check_config(env)
    assert status.key_present is False
    assert status.ok is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_setup.py -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'productagents.setup'`.

- [ ] **Step 3: Write the module**

Create `src/productagents/setup.py` with everything except `write_env` (added in Task 2):

```python
"""Provider/config preflight + .env provisioning for first-run setup.

`check_config()` is a *static* readiness check: it determines the active model,
the provider that model implies, and whether the matching API-key environment
variable is present. It never makes a network call. `write_env()` persists the
values the setup wizard collects to a `.env` file (and the live process env) so
the next run is configured.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import find_dotenv, set_key

from productagents.llm import DEFAULT_MODEL

# provider -> the environment variable holding its API key. Extensible: an
# unknown but non-empty provider falls back to a derived "<PROVIDER>_API_KEY"
# name in api_key_var_for, so new providers work without code changes.
PROVIDER_API_KEYS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google_genai": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistralai": "MISTRAL_API_KEY",
}


def provider_for(model: str, explicit_provider: str | None = None) -> str:
    """Resolve the provider name for a model id.

    An explicit `PRODUCTAGENTS_MODEL_PROVIDER` wins. Otherwise the provider is
    the prefix before the first ':' in a `provider:model` id (e.g.
    "anthropic:claude-..." -> "anthropic"). Returns "" when it can't be
    determined (a bare model id with no provider prefix).
    """
    if explicit_provider:
        return explicit_provider.strip()
    if ":" in model:
        return model.split(":", 1)[0].strip()
    return ""


def api_key_var_for(provider: str) -> str:
    """Return the API-key env var name for a provider.

    Known providers come from PROVIDER_API_KEYS; unknown but non-empty
    providers get a derived "<PROVIDER>_API_KEY" name. An empty provider
    yields "".
    """
    if not provider:
        return ""
    return PROVIDER_API_KEYS.get(provider, f"{provider.upper()}_API_KEY")


@dataclass(frozen=True)
class ConfigStatus:
    """The result of a static readiness check."""

    model: str
    provider: str
    key_var: str
    key_present: bool
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def check_config(env: Mapping[str, str] | None = None) -> ConfigStatus:
    """Statically check whether a model + matching API key are configured.

    Reads from `env` (defaults to `os.environ`). Never makes a network call.
    """
    if env is None:
        env = os.environ
    model = env.get("PRODUCTAGENTS_MODEL", DEFAULT_MODEL)
    provider = provider_for(model, env.get("PRODUCTAGENTS_MODEL_PROVIDER"))
    key_var = api_key_var_for(provider)
    key_present = bool(env.get(key_var, "").strip()) if key_var else False

    problems: list[str] = []
    if not provider:
        problems.append(
            f"Could not determine a provider from model '{model}'. "
            "Use a 'provider:model' id or set PRODUCTAGENTS_MODEL_PROVIDER."
        )
    elif not key_present:
        problems.append(
            f"Missing API key: set {key_var} for provider '{provider}'."
        )

    return ConfigStatus(
        model=model,
        provider=provider,
        key_var=key_var,
        key_present=key_present,
        problems=problems,
    )
```

> Note: `find_dotenv`/`set_key` are imported now but only used by `write_env` (Task 2). If you run Task 1 in isolation, ruff `F401` will flag them — that's expected and resolved by Task 2, which lands in the same file. If running tasks strictly one-at-a-time with a lint gate between them, temporarily omit the `from dotenv import ...` line here and add it in Task 2.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_setup.py -v`
Expected: PASS (all 11 tests).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/setup.py tests/test_setup.py
git commit -m "feat: add static config-readiness check and provider registry"
```

---

### Task 2: `.env` writer (`write_env`)

**Files:**
- Modify: `src/productagents/setup.py`
- Test: `tests/test_setup.py`

**Interfaces:**
- Produces (relied on by Tasks 3 & 5):
  - `write_env(values: Mapping[str, str], *, dotenv_path: str | os.PathLike[str] | None = None) -> str` — writes each key to the `.env` file and to `os.environ`; returns the path written.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_setup.py`:

```python
import os

from productagents.setup import write_env


def test_write_env_creates_file_and_sets_process_env(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env_file = tmp_path / ".env"

    path = write_env(
        {"PRODUCTAGENTS_MODEL": "anthropic:claude-sonnet-4-6",
         "ANTHROPIC_API_KEY": "sk-test"},
        dotenv_path=env_file,
    )

    assert path == str(env_file)
    assert env_file.exists()
    contents = env_file.read_text()
    assert "PRODUCTAGENTS_MODEL" in contents
    assert "sk-test" in contents
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test"
    assert os.environ["PRODUCTAGENTS_MODEL"] == "anthropic:claude-sonnet-4-6"


def test_write_env_preserves_existing_lines(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_VAR=keep-me\n")

    write_env({"OPENAI_API_KEY": "sk-openai"}, dotenv_path=env_file)

    contents = env_file.read_text()
    assert "EXISTING_VAR=keep-me" in contents
    assert "sk-openai" in contents
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_setup.py -k write_env -v`
Expected: FAIL with `ImportError: cannot import name 'write_env'`.

- [ ] **Step 3: Implement `write_env`**

Append to `src/productagents/setup.py` (the `find_dotenv`/`set_key` imports added in Task 1 are now used):

```python
def write_env(
    values: Mapping[str, str],
    *,
    dotenv_path: str | os.PathLike[str] | None = None,
) -> str:
    """Persist `values` to a .env file and the live process environment.

    With `dotenv_path=None`, an existing .env is discovered (walking up from the
    cwd); if none exists, `.env` in the cwd is created. Each key is written with
    python-dotenv's `set_key` (preserving other lines) and also set in
    `os.environ` so the current run picks it up immediately. Returns the path
    written.
    """
    if dotenv_path is not None:
        path = str(dotenv_path)
    else:
        path = find_dotenv(usecwd=True) or os.path.join(os.getcwd(), ".env")

    if not os.path.exists(path):
        # set_key needs an existing file on some python-dotenv versions.
        with open(path, "a", encoding="utf-8"):
            pass

    for key, value in values.items():
        set_key(path, key, value)
        os.environ[key] = value
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_setup.py -v`
Expected: PASS (all tests including the two new ones).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/setup.py tests/test_setup.py
git commit -m "feat: persist setup values to .env and process env"
```

---

### Task 3: `SetupScreen` modal

**Files:**
- Create: `src/productagents/tui/setup_screen.py`
- Test: `tests/test_setup_tui.py`

**Interfaces:**
- Consumes: `ConfigStatus`, `provider_for`, `api_key_var_for`, `write_env` from `productagents.setup`.
- Produces (relied on by Task 5):
  - `SetupScreen(status: ConfigStatus, *, writer=write_env)` — `ModalScreen[bool]`. Dismisses `True` after a successful save, `False` on cancel/escape. Input ids: `#setup-model`, `#setup-provider`, `#setup-key`; feedback `#setup-feedback`; buttons `#setup-save`, `#setup-cancel`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_setup_tui.py`:

```python
"""SetupScreen behavior, driven through a minimal host app."""

from textual.app import App

from productagents.setup import ConfigStatus
from productagents.tui.setup_screen import SetupScreen


def _missing_status():
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=False,
        problems=["Missing API key: set ANTHROPIC_API_KEY for provider 'anthropic'."],
    )


class _Host(App):
    def __init__(self, status, writer, results):
        super().__init__()
        self._status = status
        self._writer = writer
        self._results = results

    def on_mount(self):
        self.push_screen(
            SetupScreen(self._status, writer=self._writer), self._results.append
        )


async def test_setup_save_persists_values_and_dismisses_true():
    written = {}

    def writer(values, **_kwargs):
        written.update(values)

    results = []
    app = _Host(_missing_status(), writer, results)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#setup-key").value = "sk-test"
        await pilot.click("#setup-save")
        await pilot.pause()

    assert written["ANTHROPIC_API_KEY"] == "sk-test"
    assert written["PRODUCTAGENTS_MODEL"] == "anthropic:claude-sonnet-4-6"
    assert results == [True]


async def test_setup_requires_a_key():
    calls = []

    def writer(values, **_kwargs):
        calls.append(values)

    results = []
    app = _Host(_missing_status(), writer, results)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#setup-save")
        await pilot.pause()
        feedback = str(app.screen.query_one("#setup-feedback").content)

    assert "API key" in feedback
    assert calls == []
    assert results == []


async def test_setup_cancel_dismisses_false():
    def writer(values, **_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("cancel must not write")

    results = []
    app = _Host(_missing_status(), writer, results)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#setup-cancel")
        await pilot.pause()

    assert results == [False]


async def test_setup_writer_failure_is_surfaced():
    def writer(values, **_kwargs):
        raise OSError("disk full")

    results = []
    app = _Host(_missing_status(), writer, results)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#setup-key").value = "sk-test"
        await pilot.click("#setup-save")
        await pilot.pause()
        feedback = str(app.screen.query_one("#setup-feedback").content)

    assert "Could not save" in feedback
    assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_setup_tui.py -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'productagents.tui.setup_screen'`.

- [ ] **Step 3: Write the screen**

Create `src/productagents/tui/setup_screen.py`:

```python
"""First-run setup: collect a provider/model and API key, persist to .env."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from productagents.setup import (
    ConfigStatus,
    api_key_var_for,
    provider_for,
    write_env,
)


class SetupScreen(ModalScreen[bool]):
    """Collect model/provider/key, validate, and write them to .env.

    Dismisses with True when values were saved, False when cancelled.
    """

    BINDINGS: ClassVar[list] = [("escape", "cancel", "Cancel")]

    def __init__(self, status: ConfigStatus, *, writer=write_env):
        super().__init__()
        self._status = status
        self._writer = writer

    def compose(self) -> ComposeResult:
        problems = "\n".join(f"• {p}" for p in self._status.problems) or (
            "Update your model, provider, or API key."
        )
        yield Static(f"Setup needed:\n{problems}", id="setup-intro")
        yield Input(
            value=self._status.model,
            placeholder="provider:model (e.g. anthropic:claude-sonnet-4-6)",
            id="setup-model",
        )
        yield Input(
            value=self._status.provider,
            placeholder="Provider override (optional)",
            id="setup-provider",
        )
        yield Input(placeholder="API key", password=True, id="setup-key")
        yield Static("", id="setup-feedback")
        yield Button("Save", id="setup-save", variant="success")
        yield Button("Cancel", id="setup-cancel")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "setup-cancel":
            self.dismiss(False)
            return
        self._save()

    def _save(self) -> None:
        model = self.query_one("#setup-model", Input).value.strip()
        provider_override = self.query_one("#setup-provider", Input).value.strip()
        key = self.query_one("#setup-key", Input).value.strip()
        feedback = self.query_one("#setup-feedback", Static)

        provider = provider_for(model, provider_override or None)
        key_var = api_key_var_for(provider)
        if not provider:
            feedback.update("Enter a 'provider:model' id or a provider override.")
            return
        if not key:
            feedback.update(f"Enter the API key for {key_var}.")
            return

        values = {"PRODUCTAGENTS_MODEL": model, key_var: key}
        if provider_override:
            values["PRODUCTAGENTS_MODEL_PROVIDER"] = provider_override
        try:
            self._writer(values)
        except Exception as exc:  # noqa: BLE001 - surface, never crash the TUI
            feedback.update(f"Could not save: {exc}")
            return
        self.dismiss(True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_setup_tui.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/tui/setup_screen.py tests/test_setup_tui.py
git commit -m "feat: add SetupScreen for guided provider/key configuration"
```

---

### Task 4: `HomeScreen` menu

**Files:**
- Create: `src/productagents/tui/home_screen.py`
- Test: `tests/test_home_tui.py`

**Interfaces:**
- Consumes: `ConfigStatus` from `productagents.setup`. Calls `self.app.open_setup()`, `self.app.start_decision()`, `self.app.exit()` (provided by `ProductAgentsApp` in Task 5).
- Produces (relied on by Task 5):
  - `HomeScreen(status: ConfigStatus)` — `Screen`. Has `refresh_status(status: ConfigStatus) -> None`. Widget ids: `#home-status`, buttons `#home-setup`, `#home-run`, `#home-quit`. The `#home-run` button is `disabled` unless `status.ok`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_home_tui.py`:

```python
"""HomeScreen behavior, driven through a minimal host app."""

from textual.app import App
from textual.widgets import Button

from productagents.setup import ConfigStatus
from productagents.tui.home_screen import HomeScreen


def _ok_status():
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=True,
    )


def _missing_status():
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=False,
        problems=["Missing API key: set ANTHROPIC_API_KEY for provider 'anthropic'."],
    )


class _Host(App):
    def __init__(self, status):
        super().__init__()
        self._status = status
        self.events = []

    def on_mount(self):
        self.push_screen(HomeScreen(self._status))

    def open_setup(self):
        self.events.append("setup")

    def start_decision(self):
        self.events.append("run")


async def test_home_run_enabled_and_dispatches_when_ready():
    app = _Host(_ok_status())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one("#home-run", Button).disabled is False
        status_text = str(app.screen.query_one("#home-status").content)
        assert "Ready" in status_text
        await pilot.click("#home-run")
        await pilot.pause()
    assert app.events == ["run"]


async def test_home_run_disabled_when_setup_needed():
    app = _Host(_missing_status())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one("#home-run", Button).disabled is True
        status_text = str(app.screen.query_one("#home-status").content)
        assert "Setup needed" in status_text


async def test_home_setup_button_dispatches():
    app = _Host(_missing_status())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home-setup")
        await pilot.pause()
    assert app.events == ["setup"]


async def test_home_refresh_status_enables_run():
    app = _Host(_missing_status())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one("#home-run", Button).disabled is True
        app.screen.refresh_status(_ok_status())
        await pilot.pause()
        assert app.screen.query_one("#home-run", Button).disabled is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_home_tui.py -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'productagents.tui.home_screen'`.

- [ ] **Step 3: Write the screen**

Create `src/productagents/tui/home_screen.py`:

```python
"""Initial menu: set up the provider/key, run a decision, or quit."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from productagents.setup import ConfigStatus


class HomeScreen(Screen):
    """Landing menu shown on launch. Buttons delegate to app methods."""

    def __init__(self, status: ConfigStatus):
        super().__init__()
        self._status = status

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="home-status", classes="panel")
        yield Button("Set up provider & API key", id="home-setup")
        yield Button("Run a decision", id="home-run", variant="primary")
        yield Button("Quit", id="home-quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_status(self._status)

    def refresh_status(self, status: ConfigStatus) -> None:
        self._status = status
        widget = self.query_one("#home-status", Static)
        if status.ok:
            widget.update(f"[b]Ready[/b] — model {status.model}")
        else:
            problems = "\n".join(f"• {p}" for p in status.problems)
            widget.update(f"[b]Setup needed[/b]\n{problems}")
        self.query_one("#home-run", Button).disabled = not status.ok

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "home-setup":
            self.app.open_setup()
        elif event.button.id == "home-run":
            self.app.start_decision()
        elif event.button.id == "home-quit":
            self.app.exit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_home_tui.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/productagents/tui/home_screen.py tests/test_home_tui.py
git commit -m "feat: add HomeScreen landing menu with config status"
```

---

### Task 5: Wire menu + setup into `ProductAgentsApp` and `main`

**Files:**
- Modify: `src/productagents/tui/app.py`
- Modify: `src/productagents/tui/app.tcss`
- Modify: `tests/fakes.py`
- Modify: `tests/test_tui.py`
- Modify: `tests/test_approval_tui.py`
- Modify: `tests/test_reflection_tui.py`
- Modify: `tests/test_app_main.py`

**Interfaces:**
- Consumes: `HomeScreen`, `SetupScreen`, `check_config`, `write_env`.
- Produces: `ProductAgentsApp.__init__(..., config_checker=check_config, env_writer=write_env, rebuild=None, show_home=True)`; app methods `open_setup()`, `start_decision()`, `action_home()`; resilient `_build_app()` (sets `runner=None` on model-init failure, passes a `rebuild` closure); simplified `main()`.

- [ ] **Step 1: Add the `ready_status()` test helper**

Append to `tests/fakes.py`:

```python
from productagents.setup import ConfigStatus


def ready_status() -> ConfigStatus:
    """A ConfigStatus that reports the app is fully configured."""
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=True,
    )
```

- [ ] **Step 2: Update existing decision/approval/reflection tests to bypass the menu**

These tests drive the decision UI directly, so they must opt out of the home menu. Add `show_home=False` to each `ProductAgentsApp(...)` construction.

In `tests/test_tui.py`, each of the 7 constructions adds the kwarg. Example (the first, at the `recorder=recorder` call):

```python
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=recorder,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
```

Apply the same `show_home=False` kwarg to the constructions in `test_app_renders_new_analyst_panels`, `test_app_renders_recalled_lessons`, `test_app_collects_evidence_from_typed_directory`, `test_app_shows_error_for_bad_evidence_source`, `test_app_renders_and_records_provenance`, and `test_completion_event_without_panel_is_ignored`.

In `tests/test_approval_tui.py`, the construction in `test_human_reject_overrides_advisory_and_is_recorded`:

```python
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
```

In `tests/test_reflection_tui.py`, the shared `_app` helper:

```python
def _app(reflector, reader, outcome_recorder):
    return ProductAgentsApp(
        None,
        None,
        reader=reader,
        reflector=reflector,
        outcome_recorder=outcome_recorder,
        show_home=False,
    )
```

- [ ] **Step 3: Run those tests — they should still fail (kwarg not accepted yet)**

Run: `uv run pytest tests/test_tui.py tests/test_approval_tui.py tests/test_reflection_tui.py -x`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'show_home'`.

- [ ] **Step 4: Update `app.py` imports and constructor**

In `src/productagents/tui/app.py`, replace the import block. Change the top imports:

Replace:

```python
import os
import sys
from datetime import UTC, datetime
from functools import partial
from typing import ClassVar
```

with:

```python
from datetime import UTC, datetime
from functools import partial
from typing import ClassVar
```

Replace:

```python
from productagents.llm import DEFAULT_MODEL, get_model
```

with:

```python
from productagents.llm import get_model
from productagents.setup import check_config, write_env
```

Add to the screen imports (next to the existing `from productagents.tui.approval import ApprovalScreen`):

```python
from productagents.tui.home_screen import HomeScreen
from productagents.tui.setup_screen import SetupScreen
```

Replace the `BINDINGS` line:

```python
    BINDINGS: ClassVar[list] = [("ctrl+r", "reflect", "Reflect on a decision")]
```

with:

```python
    BINDINGS: ClassVar[list] = [
        ("ctrl+r", "reflect", "Reflect on a decision"),
        ("ctrl+h", "home", "Menu"),
    ]
```

Replace the `__init__` signature/body. Change:

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
        self._reader = reader
        self._outcome_reader = outcome_reader
        self._reflector = reflector
        self._outcome_recorder = outcome_recorder
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []
```

to:

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
        config_checker=check_config,
        env_writer=write_env,
        rebuild=None,
        show_home=True,
    ):
        super().__init__()
        self._runner = runner
        self._evidence = evidence
        self._collector = collector
        self._recorder = recorder
        self._reader = reader
        self._outcome_reader = outcome_reader
        self._reflector = reflector
        self._outcome_recorder = outcome_recorder
        self._config_checker = config_checker
        self._env_writer = env_writer
        self._rebuild = rebuild
        self._show_home = show_home
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []
```

- [ ] **Step 5: Add the menu push to `on_mount` and the orchestration methods**

In `src/productagents/tui/app.py`, replace the end of `on_mount`. Change:

```python
        self.query_one("#evidence-provenance", Static).border_title = "Evidence Sources"
```

to:

```python
        self.query_one("#evidence-provenance", Static).border_title = "Evidence Sources"
        if self._show_home:
            self._open_home()
```

Then add these methods immediately after `on_mount` (before `on_input_submitted`):

```python
    def _open_home(self) -> None:
        status = self._config_checker()
        self.push_screen(HomeScreen(status))
        if not status.ok:
            self.open_setup()

    def open_setup(self) -> None:
        self.push_screen(
            SetupScreen(self._config_checker(), writer=self._env_writer),
            self._after_setup,
        )

    def _after_setup(self, saved: bool | None) -> None:
        if saved and self._rebuild is not None:
            try:
                self._runner, self._reflector = self._rebuild()
            except Exception:  # noqa: BLE001 - stay on the menu, let the user retry
                pass
        screen = self.screen
        if isinstance(screen, HomeScreen):
            screen.refresh_status(self._config_checker())

    def start_decision(self) -> None:
        # Reveal the base decision UI by popping the HomeScreen.
        if isinstance(self.screen, HomeScreen):
            self.pop_screen()

    def action_home(self) -> None:
        if not isinstance(self.screen, HomeScreen):
            self._open_home()
```

- [ ] **Step 6: Make `_build_app` resilient and simplify `main`**

In `src/productagents/tui/app.py`, replace:

```python
def _build_app() -> ProductAgentsApp:
    model = get_model()
    graph = build_graph(model, human_in_the_loop=True)
    evidence = load_scenario("sample")
    return ProductAgentsApp(
        partial(run_decision, graph),
        evidence,
        reflector=partial(reflect, model=model),
    )


def main() -> None:
    load_env()
    try:
        app = _build_app()
    except Exception as exc:
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

with:

```python
def _build_app() -> ProductAgentsApp:
    def rebuild():
        model = get_model()
        graph = build_graph(model, human_in_the_loop=True)
        return partial(run_decision, graph), partial(reflect, model=model)

    try:
        runner, reflector = rebuild()
    except Exception:  # noqa: BLE001 - launch into setup instead of crashing
        runner, reflector = None, None
    evidence = load_scenario("sample")
    return ProductAgentsApp(
        runner,
        evidence,
        reflector=reflector,
        rebuild=rebuild,
    )


def main() -> None:
    load_env()
    app = _build_app()
    app.run()
```

- [ ] **Step 7: Add CSS for the new screens**

Append to `src/productagents/tui/app.tcss`:

```css
#home-status {
    margin: 1;
    border: round $primary;
    padding: 1;
    height: auto;
}

#home-setup, #home-run, #home-quit {
    margin: 0 1;
    width: 100%;
}

SetupScreen {
    align: center middle;
}

#setup-intro {
    margin: 1;
    padding: 1;
    border: round $warning;
    height: auto;
}

#setup-model, #setup-provider, #setup-key {
    margin: 0 1;
}

#setup-feedback {
    margin: 1;
    color: $error;
    height: auto;
}

#setup-save, #setup-cancel {
    margin: 0 1;
}
```

- [ ] **Step 8: Replace the entry-point tests**

In `tests/test_app_main.py`, replace the whole file body (keep the module docstring) with:

```python
"""Tests for the productagents entry point wiring."""

from productagents.tui import app as app_module


def test_main_loads_env_before_building_app(monkeypatch):
    calls = []

    def fake_load_env():
        calls.append("load_env")
        return True

    class _StubApp:
        def run(self):
            calls.append("run")

    def fake_build_app():
        calls.append("build_app")
        return _StubApp()

    monkeypatch.setattr(app_module, "load_env", fake_load_env)
    monkeypatch.setattr(app_module, "_build_app", fake_build_app)

    app_module.main()

    assert calls == ["load_env", "build_app", "run"]


def test_build_app_is_resilient_when_model_init_fails(monkeypatch):
    def boom():
        raise RuntimeError("no api key")

    monkeypatch.setattr(app_module, "get_model", boom)

    app = app_module._build_app()

    # Model init failed, but the app still builds so it can route to setup.
    assert app._runner is None
    assert app._reflector is None
    assert app._rebuild is not None
```

Also delete `test_main_reports_clear_error_when_model_init_fails` from `tests/test_tui.py` (the behavior it asserted — printing a hint and `SystemExit(1)` — is intentionally replaced by the graceful setup flow). Remove the now-unused `import pytest` from `tests/test_tui.py` if nothing else uses it (check the file; the integration tests added in Step 9 do not require `pytest`).

- [ ] **Step 9: Add integration tests for the menu/setup flow**

Append to `tests/test_tui.py` (it already imports `partial`, `build_graph`, `run_decision`, schema classes, `ProductAgentsApp`, `FakeChatModel`, and defines `_runner_and_evidence()`):

```python
from textual.widgets import Button

from productagents.setup import ConfigStatus
from productagents.tui.home_screen import HomeScreen
from productagents.tui.setup_screen import SetupScreen


def _ok_status():
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=True,
    )


def _missing_status():
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=False,
        problems=["Missing API key: set ANTHROPIC_API_KEY for provider 'anthropic'."],
    )


async def test_app_shows_home_menu_when_config_ready():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=_ok_status,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
        assert app.screen.query_one("#home-run", Button).disabled is False


async def test_app_auto_opens_setup_when_config_incomplete():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=_missing_status,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, SetupScreen)


async def test_app_run_from_menu_reveals_decision_ui():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=_ok_status,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home-run")
        await pilot.pause()
        assert not isinstance(app.screen, HomeScreen)
        # The decision input is now on the active screen.
        app.query_one("#initiative-title")


async def test_setup_save_rebuilds_runner_and_refreshes_home():
    runner, evidence = _runner_and_evidence()
    state = {"ok": False}

    def checker():
        return _ok_status() if state["ok"] else _missing_status()

    written = {}

    def writer(values, **_kwargs):
        written.update(values)
        state["ok"] = True

    rebuilt = []

    def rebuild():
        rebuilt.append(True)
        return runner, None

    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=checker,
        env_writer=writer,
        rebuild=rebuild,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        # Incomplete config auto-opened the setup screen.
        assert isinstance(app.screen, SetupScreen)
        app.screen.query_one("#setup-key").value = "sk-test"
        await pilot.click("#setup-save")
        await pilot.pause()
        # Back on the home menu, now reporting Ready with run enabled.
        assert isinstance(app.screen, HomeScreen)
        assert app.screen.query_one("#home-run", Button).disabled is False

    assert written["ANTHROPIC_API_KEY"] == "sk-test"
    assert rebuilt == [True]
```

- [ ] **Step 10: Run the full suite**

Run: `uv run pytest`
Expected: PASS, coverage ≥ 90%. If `app.py`'s `action_home` is reported uncovered and it drops below the gate, add a quick test:

```python
async def test_ctrl_h_reopens_menu_from_decision_ui():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=_ok_status,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home-run")  # reveal decision UI
        await pilot.pause()
        await pilot.press("ctrl+h")  # back to the menu
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
```

- [ ] **Step 11: Lint**

Run: `uv run ruff check src/productagents/tui/app.py tests/`
Expected: PASS (no unused-import / blind-except findings).

- [ ] **Step 12: Commit**

```bash
git add src/productagents/tui/app.py src/productagents/tui/app.tcss \
  tests/fakes.py tests/test_tui.py tests/test_approval_tui.py \
  tests/test_reflection_tui.py tests/test_app_main.py
git commit -m "feat: launch into a home menu with guided first-run setup"
```

---

### Task 6: Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `src/productagents/CLAUDE.md`
- Modify: `src/productagents/tui/CLAUDE.md`
- Modify: `.env.example`

**Interfaces:** None (docs only).

- [ ] **Step 1: Update the package map in `CLAUDE.md`**

In `CLAUDE.md`, add a `setup.py` line to the directory tree under `src/productagents/`, immediately after the `llm.py` line:

```
├── setup.py              # config readiness check (check_config) + .env writer (write_env)
```

And in the same tree, under `tui/`, update the screens line to include the new screens:

```
│   ├── app.py · app.tcss · approval.py · reflection.py · home_screen.py · setup_screen.py
```

- [ ] **Step 2: Document the first-run flow in `CLAUDE.md`**

In `CLAUDE.md`, under "### Runtime configuration (env vars)", add a paragraph after the bullet list:

```markdown
On launch the TUI shows a **home menu** (Set up / Run a decision / Quit) and runs
a **static readiness check** (`setup.check_config`): it derives the provider from
`PRODUCTAGENTS_MODEL`, looks up the matching API-key env var, and verifies it is
present. If anything is missing it auto-opens a **SetupScreen** that writes the
model/provider/key to `.env` (`setup.write_env`) and rebuilds the model so the
new config takes effect without a restart. The check never makes a network call.
```

- [ ] **Step 3: Update `src/productagents/CLAUDE.md`**

In `src/productagents/CLAUDE.md`, add a row to the Layers table immediately after the `llm.py` row:

```markdown
| `setup.py` | Static config-readiness check + `.env` provisioning. `check_config()` resolves provider→key-var and verifies the key is set (no network). `write_env()` persists collected values via `python-dotenv` and `os.environ`. Used by the TUI's home/setup screens, **not** by graph nodes. |
```

- [ ] **Step 4: Update `src/productagents/tui/CLAUDE.md`**

In `src/productagents/tui/CLAUDE.md`, add two rows to the Files table:

```markdown
| `home_screen.py` | `HomeScreen` (`Screen`). Landing menu shown on launch; buttons delegate to `app.open_setup()` / `app.start_decision()` / `app.exit()`. `refresh_status()` updates the readiness line and enables/disables the run button. |
| `setup_screen.py` | `SetupScreen` (`ModalScreen[bool]`). Collects model/provider/key, validates, and writes them via the injected `writer` (`setup.write_env`). Dismisses `True` on save, `False` on cancel. |
```

And add a short subsection after "## HITL pause":

```markdown
## First-run menu & setup

`on_mount` pushes `HomeScreen` (skipped when `show_home=False`, used by the
decision/approval/reflection tests). If `config_checker()` reports the app isn't
ready, `open_setup()` pushes `SetupScreen` on top. A successful save calls the
injected `rebuild()` to rebuild the runner/reflector with the new config, then
refreshes the home status. "Run a decision" pops `HomeScreen` to reveal the base
decision UI; `ctrl+h` re-opens the menu. New DI seams on `ProductAgentsApp`:
`config_checker` (default `setup.check_config`), `env_writer` (default
`setup.write_env`), `rebuild` (default `None`; `main` injects the real builder),
and `show_home`.
```

- [ ] **Step 5: Expand `.env.example` with the generic provider note**

In `.env.example`, under the "Provider API key" section, add a comment line after the OpenAI line:

```
# GOOGLE_API_KEY="your-google-api-key"
# For any other provider, set PRODUCTAGENTS_MODEL_PROVIDER and that provider's
# <PROVIDER>_API_KEY (e.g. provider "cohere" -> COHERE_API_KEY).
```

- [ ] **Step 6: Verify the `.env.example` test still passes**

There is a `tests/test_env_example.py`. Run it to make sure the additions don't break any structural assertion:

Run: `uv run pytest tests/test_env_example.py -v`
Expected: PASS. If it asserts an exact set of keys, reconcile by keeping the new lines commented (they are) so they aren't parsed as active keys.

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md src/productagents/CLAUDE.md src/productagents/tui/CLAUDE.md .env.example
git commit -m "docs: document the first-run home menu and setup flow"
```

---

## Self-Review

**Spec coverage:**
- "checks if the app has everything it needs" → Task 1 (`check_config`, static provider+key check).
- "initial screen with a menu (setup / decision-making / quit)" → Task 4 (`HomeScreen`) + Task 5 (`on_mount` push, `start_decision`, `exit`).
- "if config is incomplete, push a modal SetupScreen" → Task 3 (`SetupScreen`) + Task 5 (`_open_home` auto-opens setup when `not status.ok`).
- "write to .env" → Task 2 (`write_env`).
- "static check" → Task 1 (no network).
- "generic/extensible providers" → Task 1 (`PROVIDER_API_KEYS` + derived `<PROVIDER>_API_KEY` fallback).
- Same-session effect after setup → Task 5 (`rebuild` closure in `_build_app`, called from `_after_setup`).

**Placeholder scan:** No TBD/TODO; every code step shows complete code; every test step shows full assertions.

**Type consistency:** `ConfigStatus(model, provider, key_var, key_present, problems)` + `.ok` is used identically in Tasks 1, 3, 4, 5 tests. `provider_for`, `api_key_var_for`, `write_env`, `check_config` signatures match across tasks. Screen widget ids (`#setup-model/provider/key/feedback/save/cancel`, `#home-status/setup/run/quit`) are consistent between screen source and tests. App seam names (`config_checker`, `env_writer`, `rebuild`, `show_home`) match between the constructor (Task 5 Step 4) and all test call sites (Steps 2 & 9).

**Known risk noted in-plan:** `set_key` file-creation behavior varies by python-dotenv version — Task 2 touches the file first to be safe. Task 1's `from dotenv import ...` is unused until Task 2 — flagged in a note for strict per-task lint gating.
