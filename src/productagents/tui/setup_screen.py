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
