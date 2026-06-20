"""Textual TUI for running a ProductAgents decision and showing it live."""

import os
import sys
from datetime import UTC, datetime
from functools import partial

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from productagents.evidence import load_scenario
from productagents.graph import build_graph
from productagents.llm import DEFAULT_MODEL, get_model
from productagents.memory import read_decisions, record_decision
from productagents.runner import (
    DebateTurnEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    NodeCompleteEvent,
    ProgressEvent,
    RiskAssessmentEvent,
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

    def __init__(
        self, runner, evidence, *, recorder=record_decision, reader=read_decisions
    ):
        super().__init__()
        self._runner = runner
        self._evidence = evidence
        self._recorder = recorder
        self._reader = reader
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(
            placeholder="Describe the initiative and press Enter…",
            id="initiative-title",
        )
        with Horizontal(id="analysts"):
            yield Static("Waiting…", id="customer_research", classes="panel")
            yield Static("Waiting…", id="product_analytics", classes="panel")
        with VerticalScroll(id="debate-scroll"):
            yield Static("Waiting…", id="debate")
        yield Static("Waiting…", id="strategist", classes="panel")
        with VerticalScroll(id="risk-scroll"):
            yield Static("Waiting…", id="risk")
        yield Static("Waiting…", id="governance", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        for node_id, role in _PANELS.items():
            self.query_one(f"#{node_id}", Static).border_title = role
        self.query_one("#debate-scroll").border_title = "Advocate vs Skeptic Debate"
        self.query_one("#risk-scroll").border_title = "Risk Team"
        self.query_one(
            "#governance", Static
        ).border_title = "Portfolio Manager (Governance)"

    def on_input_submitted(self, message: Input.Submitted) -> None:
        title = message.value.strip()
        if not title:
            return
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._debate_lines = []
        self._risk_lines = []
        self.query_one("#debate", Static).update("…")
        self.query_one("#risk", Static).update("…")
        self.query_one("#governance", Static).update("…")
        self._run(Initiative(title=title, description=title))

    @work(exclusive=True)
    async def _run(self, initiative: Initiative) -> None:
        recommendation = None
        reports = []
        debate = []
        risks = []
        governance = None
        portfolio = self._reader()
        async for event in self._runner(
            initiative, self._evidence, portfolio=portfolio
        ):
            if isinstance(event, ProgressEvent):
                if event.node in _PANELS:
                    self.query_one(f"#{event.node}", Static).update(
                        f"… {event.message}"
                    )
            elif isinstance(event, NodeCompleteEvent):
                report = event.report
                body = "\n".join(f"• {f}" for f in report.findings) or "(no findings)"
                self.query_one(f"#{event.node}", Static).update(body)
            elif isinstance(event, DebateTurnEvent):
                self._debate_lines.append(
                    f"[{event.side} · round {event.round}] {event.argument}"
                )
                self.query_one("#debate", Static).update(
                    "\n\n".join(self._debate_lines)
                )
            elif isinstance(event, RiskAssessmentEvent):
                self._risk_lines.append(
                    f"[{event.role} · {event.level}] {event.rationale}"
                )
                self.query_one("#risk", Static).update("\n\n".join(self._risk_lines))
            elif isinstance(event, GovernanceVerdictEvent):
                self.query_one("#governance", Static).update(
                    f"[b]{event.verdict}[/b]\n\n{event.rationale}"
                )
            elif isinstance(event, FinishedEvent):
                recommendation = event.recommendation
                reports = event.reports
                debate = event.debate
                risks = event.risks
                governance = event.governance
                self._render_recommendation(recommendation)

        if recommendation is not None:
            self._recorder(
                DecisionRecord(
                    initiative=initiative,
                    recommendation=recommendation,
                    reports=reports,
                    debate=debate,
                    risks=risks,
                    governance=governance,
                    timestamp=datetime.now(UTC).isoformat(),
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


def _build_app() -> ProductAgentsApp:
    graph = build_graph(get_model())
    evidence = load_scenario("sample")
    return ProductAgentsApp(partial(run_decision, graph), evidence)


def main() -> None:
    try:
        app = _build_app()
    except Exception as exc:
        model = os.environ.get("PRODUCTAGENTS_MODEL", DEFAULT_MODEL)
        print(
            f"Failed to start ProductAgents: {exc}\n"
            f"Check that PRODUCTAGENTS_MODEL ('{model}') is valid and the "
            f"matching provider API key is set (e.g. ANTHROPIC_API_KEY).",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    app.run()
