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
