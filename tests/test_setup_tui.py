"""SetupScreen behavior, driven through a minimal host app."""

from productagents.app.setup import ConfigStatus
from productagents.app.tui.setup_screen import SetupScreen
from textual.app import App
from textual.widgets import Select


def _missing_status():
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=False,
        problems=["Missing API key: set ANTHROPIC_API_KEY for provider 'anthropic'."],
    )


def _no_provider_status():
    return ConfigStatus(
        model="",
        provider="",
        key_var="",
        key_present=False,
        problems=["Could not determine a provider."],
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
        # "anthropic" is pre-selected from status; model is pre-filled
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


async def test_setup_requires_provider():
    calls = []

    def writer(values, **_kwargs):
        calls.append(values)

    results = []
    app = _Host(_no_provider_status(), writer, results)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#setup-key").value = "sk-test"
        await pilot.click("#setup-save")
        await pilot.pause()
        feedback = str(app.screen.query_one("#setup-feedback").content)

    assert "Choose a provider" in feedback
    assert calls == []
    assert results == []


async def test_setup_provider_selection_updates_model_and_key_label():
    written = {}

    def writer(values, **_kwargs):
        written.update(values)

    results = []
    app = _Host(_missing_status(), writer, results)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Switch to OpenAI — model and key label should update
        app.screen.query_one("#setup-provider", Select).value = "openai"
        await pilot.pause()
        model_val = app.screen.query_one("#setup-model").value
        key_label = str(app.screen.query_one("#setup-key-label").content)
        assert model_val == "openai:gpt-4o"
        assert "OPENAI_API_KEY" in key_label
        # Save with the OpenAI key
        app.screen.query_one("#setup-key").value = "sk-openai-test"
        await pilot.click("#setup-save")
        await pilot.pause()

    assert written["OPENAI_API_KEY"] == "sk-openai-test"
    assert written["PRODUCTAGENTS_MODEL"] == "openai:gpt-4o"
    assert results == [True]


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
