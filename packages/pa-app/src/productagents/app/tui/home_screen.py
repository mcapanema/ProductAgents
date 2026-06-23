"""Initial menu: set up the provider/key, run a decision, or quit."""

from typing import Any, cast

from productagents.app.setup import ConfigStatus
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


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
        app = cast(Any, self.app)
        if event.button.id == "home-setup":
            app.open_setup()
        elif event.button.id == "home-run":
            app.start_decision()
        elif event.button.id == "home-quit":
            self.app.exit()
