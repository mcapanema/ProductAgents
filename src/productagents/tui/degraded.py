"""Degraded-run prompt: the pipeline could not produce a recommendation.

Shown when a decision run fails fast because the strategist could not synthesize
a recommendation (typically a cascade of transient provider errors). Rather than
silently aborting or forcing an uninformed approval, the human chooses how to
proceed; the pressed button's id is returned via `Screen.dismiss`.
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class DegradedRunScreen(ModalScreen[str]):
    """Offer Retry / Make a decision anyway / Quit for a degraded run."""

    def compose(self) -> ComposeResult:
        yield Static(
            "This run could not produce a recommendation — the pipeline hit "
            "provider errors before synthesizing a decision. See Status / Errors "
            "for details.\n\nWhat would you like to do?",
            id="degraded-message",
        )
        yield Button("Retry the run", id="retry", variant="primary")
        yield Button("Make a decision anyway", id="decide")
        yield Button("Quit (discard)", id="quit", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)
