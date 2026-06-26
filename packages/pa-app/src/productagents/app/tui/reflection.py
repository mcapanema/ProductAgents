"""Reflection mode: record the actual outcome of a past decision."""

from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option


class ReflectionScreen(Screen):
    """Pick a past decision, describe what happened, and record the reflection."""

    BINDINGS: ClassVar[list] = [("escape", "app.pop_screen", "Back")]

    def __init__(self, *, reflector, reader, outcome_recorder):
        super().__init__()
        self._reflector = reflector
        self._reader = reader
        self._outcome_recorder = outcome_recorder
        self._decisions = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList(id="decision-list")
        yield Input(placeholder="What actually happened?", id="outcome-note")
        yield Static("Pick a decision and describe the outcome.", id="reflection")
        yield Footer()

    def on_mount(self) -> None:
        self._load_decisions()

    @work(exclusive=True)
    async def _load_decisions(self) -> None:
        self._decisions = list(reversed(await self._reader()))
        option_list = self.query_one("#decision-list", OptionList)
        for decision in self._decisions:
            option_list.add_option(
                Option(
                    f"{decision.initiative.title} — "
                    f"{decision.recommendation.recommendation}",
                    id=decision.decision_id,
                )
            )
        if self._decisions:
            option_list.highlighted = 0
        self.query_one("#outcome-note", Input).focus()

    def on_input_submitted(self, message: Input.Submitted) -> None:
        message.stop()
        note = message.value.strip()
        if not note or not self._decisions:
            return
        index = self.query_one("#decision-list", OptionList).highlighted or 0
        self._reflect(self._decisions[index], note)

    @work(exclusive=True)
    async def _reflect(self, decision, note: str) -> None:
        self.query_one("#reflection", Static).update("Reflecting…")
        try:
            outcome = await self._reflector(decision, note)
            outcomes = "\n".join(f"• {o}" for o in outcome.actual_outcomes) or "(none)"
            lessons = (
                "\n".join(f"• {lesson}" for lesson in outcome.lessons_learned)
                or "(none)"
            )
            self.query_one("#reflection", Static).update(
                f"Prediction accuracy: {outcome.prediction_accuracy:.0%}\n\n"
                f"Actual outcomes:\n{outcomes}\n\n"
                f"Lessons learned:\n{lessons}"
            )
            await self._outcome_recorder(outcome)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash
            self.query_one("#reflection", Static).update(f"Reflection failed: {exc}")
