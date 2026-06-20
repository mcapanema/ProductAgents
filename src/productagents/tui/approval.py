"""Approval mode: a human reviewer makes the final governance call.

Shown when a human-in-the-loop run pauses after the Portfolio Manager produces
its advisory verdict. The reviewer approves, rejects, or requests further
analysis (with an optional note); the choice is returned to the graph as a
`HumanDecision` via `Screen.dismiss`.
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from productagents.schemas import GovernanceVerdict, HumanDecision


class ApprovalScreen(ModalScreen[HumanDecision]):
    """Present the advisory verdict and capture the human's final decision."""

    def __init__(self, advisory: GovernanceVerdict | None):
        super().__init__()
        self._advisory = advisory

    def compose(self) -> ComposeResult:
        rec = self._advisory.verdict if self._advisory else "n/a"
        rationale = self._advisory.rationale if self._advisory else ""
        yield Static(
            f"Portfolio Manager recommends: [b]{rec}[/b]\n\n{rationale}",
            id="advisory",
        )
        yield Input(placeholder="Optional note for the record…", id="note")
        yield Button("Approve", id="approve", variant="success")
        yield Button("Reject", id="reject", variant="error")
        yield Button("Request analysis", id="request_analysis")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        note = self.query_one("#note", Input).value.strip()
        self.dismiss(HumanDecision(verdict=event.button.id, rationale=note))
