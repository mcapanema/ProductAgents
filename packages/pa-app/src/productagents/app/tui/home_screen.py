"""Initial menu: set up the provider/key, sync data, run a decision, or quit."""

from typing import Any, cast

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from productagents.app.setup import ConfigStatus


class HomeScreen(Screen):
    """Landing menu shown on launch. Buttons delegate to app methods."""

    def __init__(
        self, status: ConfigStatus, connectors_line: str = "", workspace_name: str = ""
    ):
        super().__init__()
        self._status = status
        self._connectors_line = connectors_line
        self._workspace_name = workspace_name

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="home-workspace", classes="panel")
        yield Static("", id="home-status", classes="panel")
        yield Static("", id="home-connectors", classes="panel")
        yield Button("Set up provider & API key", id="home-setup")
        yield Button("Sync data sources", id="home-sync")
        yield Button("Check connector health", id="home-health")
        yield Button("Run a decision", id="home-run", variant="primary")
        yield Button("Quit", id="home-quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        if self._workspace_name:
            self.query_one("#home-workspace", Static).update(
                f"[b]Workspace[/b] — {self._workspace_name}"
            )
        self.refresh_status(self._status)
        self.refresh_connectors(self._connectors_line)

    def refresh_status(self, status: ConfigStatus) -> None:
        self._status = status
        widget = self.query_one("#home-status", Static)
        if status.ok:
            widget.update(f"[b]Ready[/b] — model {status.model}")
        else:
            problems = "\n".join(f"• {p}" for p in status.problems)
            widget.update(f"[b]Setup needed[/b]\n{problems}")
        self.query_one("#home-run", Button).disabled = not status.ok

    def refresh_connectors(self, line: str) -> None:
        self._connectors_line = line
        self.query_one("#home-connectors", Static).update(line or "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        app = cast(Any, self.app)
        if event.button.id == "home-setup":
            app.open_setup()
        elif event.button.id == "home-sync":
            app.sync_sources()
        elif event.button.id == "home-health":
            app.check_health()
        elif event.button.id == "home-run":
            app.start_decision()
        elif event.button.id == "home-quit":
            self.app.exit()
