"""First-run setup: pick a provider, confirm the model, paste the API key."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Select, Static
from textual.widgets.select import NoSelection

from productagents.setup import (
    PROVIDERS,
    ConfigStatus,
    write_env,
)

_PROVIDER_OPTIONS = [(info.label, pid) for pid, info in PROVIDERS.items()]


class SetupScreen(ModalScreen[bool]):
    """Pick a provider from a list, confirm the model string, paste the API key.

    Dismisses with True when values were saved, False when cancelled.
    """

    BINDINGS: ClassVar[list] = [("escape", "cancel", "Cancel")]

    def __init__(self, status: ConfigStatus, *, writer=write_env):
        super().__init__()
        self._status = status
        self._writer = writer

    def compose(self) -> ComposeResult:
        problems = "\n".join(f"• {p}" for p in self._status.problems) or (
            "Update your provider and API key."
        )
        initial_pid = (
            self._status.provider if self._status.provider in PROVIDERS else Select.NULL
        )
        initial_info = PROVIDERS.get(self._status.provider)

        yield Static(f"Setup needed:\n{problems}", id="setup-intro")
        yield Select(
            _PROVIDER_OPTIONS,
            value=initial_pid,
            allow_blank=True,
            prompt="Choose a provider…",
            id="setup-provider",
        )
        yield Input(
            value=initial_info.default_model if initial_info else "",
            placeholder="provider:model-id",
            id="setup-model",
        )
        key_label = f"API key ({initial_info.key_var})" if initial_info else "API key"
        yield Static(key_label, id="setup-key-label")
        yield Input(
            placeholder="Paste your API key here", password=True, id="setup-key"
        )
        yield Static("", id="setup-feedback")
        yield Button("Save", id="setup-save", variant="success")
        yield Button("Cancel", id="setup-cancel")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "setup-provider":
            return
        value = event.value
        if isinstance(value, NoSelection):
            self.query_one("#setup-model", Input).value = ""
            self.query_one("#setup-key-label", Static).update("API key")
            return
        info = PROVIDERS[str(value)]
        self.query_one("#setup-model", Input).value = info.default_model
        self.query_one("#setup-key-label", Static).update(f"API key ({info.key_var})")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "setup-cancel":
            self.dismiss(False)
            return
        self._save()

    def _save(self) -> None:
        provider_id = self.query_one("#setup-provider", Select).value
        model = self.query_one("#setup-model", Input).value.strip()
        key = self.query_one("#setup-key", Input).value.strip()
        feedback = self.query_one("#setup-feedback", Static)

        if isinstance(provider_id, NoSelection):
            feedback.update("Choose a provider from the list.")
            return

        info = PROVIDERS[str(provider_id)]
        if not key:
            feedback.update(f"Enter the API key ({info.key_var}).")
            return

        values = {"PRODUCTAGENTS_MODEL": model or info.default_model, info.key_var: key}
        try:
            self._writer(values)
        except Exception as exc:  # noqa: BLE001 - surface, never crash the TUI
            feedback.update(f"Could not save: {exc}")
            return
        self.dismiss(True)
