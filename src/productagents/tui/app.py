"""Textual TUI for running a ProductAgents decision and showing it live."""

from datetime import datetime, timezone
from functools import partial

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, Static

from productagents.evidence import load_scenario
from productagents.graph import build_graph
from productagents.llm import get_model
from productagents.memory import record_decision
from productagents.runner import (
    FinishedEvent,
    NodeCompleteEvent,
    ProgressEvent,
    run_decision,
)
from productagents.schemas import DecisionRecord, Initiative

_PANELS = {
    "customer_research": "Customer Research Analyst",
    "product_analytics": "Product Analytics Analyst",
    "strategist": "Product Strategist",
}


class ProductAgentsApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "ProductAgents"

    def __init__(self, runner, evidence, *, recorder=record_decision, scenario="sample"):
        super().__init__()
        self._runner = runner
        self._evidence = evidence
        self._recorder = recorder
        self._scenario = scenario

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(
            placeholder="Describe the initiative and press Enter…",
            id="initiative-title",
        )
        with Horizontal(id="panels"):
            yield Static("Waiting…", id="customer_research", classes="panel")
            yield Static("Waiting…", id="product_analytics", classes="panel")
            yield Static("Waiting…", id="strategist", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        for node_id, role in _PANELS.items():
            self.query_one(f"#{node_id}", Static).border_title = role

    def on_input_submitted(self, message: Input.Submitted) -> None:
        title = message.value.strip()
        if not title:
            return
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._run(Initiative(title=title, description=title))

    @work(exclusive=True)
    async def _run(self, initiative: Initiative) -> None:
        recommendation = None
        reports = []
        async for event in self._runner(initiative, self._evidence):
            if isinstance(event, ProgressEvent):
                if event.node in _PANELS:
                    self.query_one(f"#{event.node}", Static).update(
                        f"… {event.message}"
                    )
            elif isinstance(event, NodeCompleteEvent):
                report = event.report
                body = "\n".join(f"• {f}" for f in report.findings) or "(no findings)"
                self.query_one(f"#{event.node}", Static).update(body)
            elif isinstance(event, FinishedEvent):
                recommendation = event.recommendation
                reports = event.reports
                self._render_recommendation(recommendation)

        if recommendation is not None:
            self._recorder(
                DecisionRecord(
                    initiative=initiative,
                    recommendation=recommendation,
                    reports=reports,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

    def _render_recommendation(self, recommendation) -> None:
        text = (
            f"[b]{recommendation.recommendation}[/b]\n\n"
            f"Confidence: {recommendation.confidence:.0%}\n\n"
            f"{recommendation.rationale}\n\n"
            "Expected outcomes:\n"
            + "\n".join(f"• {o}" for o in recommendation.expected_outcomes)
        )
        self.query_one("#strategist", Static).update(text)


def main() -> None:
    graph = build_graph(get_model())
    evidence = load_scenario("sample")
    app = ProductAgentsApp(partial(run_decision, graph), evidence, scenario="sample")
    app.run()
