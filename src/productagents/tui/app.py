"""Textual TUI for running a ProductAgents decision and showing it live."""

from datetime import UTC, datetime
from functools import partial
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.theme import Theme
from textual.widgets import Footer, Header, Input, Static

from productagents.agents.reflection import reflect
from productagents.config import load_env
from productagents.evidence import EvidenceError, collect_evidence, load_scenario
from productagents.graph import build_graph
from productagents.llm import get_model
from productagents.logging_config import configure_logging
from productagents.memory import (
    read_decisions,
    read_outcomes,
    record_decision,
    record_outcome,
)
from productagents.runner import (
    DebateTurnEvent,
    FinalVerdictEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    JudgmentEvent,
    NodeCompleteEvent,
    NodeErrorEvent,
    ProgressEvent,
    RecallEvent,
    RiskAssessmentEvent,
    run_decision,
)
from productagents.schemas import DecisionRecord, GovernanceVerdict, Initiative
from productagents.setup import check_config, write_env
from productagents.tui.approval import ApprovalScreen
from productagents.tui.degraded import DegradedRunScreen
from productagents.tui.home_screen import HomeScreen
from productagents.tui.reflection import ReflectionScreen
from productagents.tui.setup_screen import SetupScreen

_TITLES = {
    "customer_research": "Customer Research Analyst",
    "product_analytics": "Product Analytics Analyst",
    "market": "Market Analyst",
    "business": "Business Analyst",
    "technical": "Technical Analyst",
    "recall": "Lessons from Past Decisions",
    "strategist": "Product Strategist",
    "judgment": "Quality Judge",
    "evidence-provenance": "Evidence Sources",
    "debate-scroll": "Advocate vs Skeptic Debate",
    "risk-scroll": "Risk Team",
    "governance": "Portfolio Manager (Governance)",
    "status-log": "Status / Errors",
}

# Runner node names whose live widget differs from the node id.
_WIDGET_FOR_NODE = {
    "debate": "debate-scroll",
    "risk": "risk-scroll",
}

# Analyst node ids that have a dedicated panel widget (used to gate updates).
_PANELS = {
    "customer_research",
    "product_analytics",
    "market",
    "business",
    "technical",
    "recall",
    "strategist",
}

_THEME = Theme(
    name="productagents",
    primary="#38bdf8",
    secondary="#a78bfa",
    accent="#f59e0b",
    success="#22c55e",
    warning="#fb923c",
    error="#ef4444",
    surface="#1e293b",
    panel="#0f172a",
    dark=True,
)

_STATE_ICON = {
    "idle": "·",
    "waiting": "◌",
    "running": "●",
    "done": "✓",
    "failed": "✗",
    "warning": "⚠",
}

# Spinner frames for the "running" state (a rotating filled circle).
_SPINNER_FRAMES = "◐◓◑◒"

# Downstream panels that depend on upstream output; they show "waiting" at the
# start of a run until their first event flips them to running.
_WAITING_AT_START = {
    "debate-scroll",
    "strategist",
    "judgment",
    "risk-scroll",
    "governance",
}


class ProductAgentsApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "ProductAgents"
    BINDINGS: ClassVar[list] = [
        ("ctrl+r", "reflect", "Reflect on a decision"),
        ("ctrl+h", "home", "Menu"),
    ]

    def __init__(
        self,
        runner,
        evidence,
        *,
        collector=collect_evidence,
        recorder=record_decision,
        reader=read_decisions,
        outcome_reader=read_outcomes,
        reflector=None,
        outcome_recorder=record_outcome,
        config_checker=check_config,
        env_writer=write_env,
        rebuild=None,
        show_home=True,
        runner_error=None,
    ):
        super().__init__()
        self._runner = runner
        self._runner_error = runner_error
        self._evidence = evidence
        self._collector = collector
        self._recorder = recorder
        self._reader = reader
        self._outcome_reader = outcome_reader
        self._reflector = reflector
        self._outcome_recorder = outcome_recorder
        self._config_checker = config_checker
        self._env_writer = env_writer
        self._rebuild = rebuild
        self._show_home = show_home
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []
        self._status_lines: list[str] = []
        self._spinning: set[str] = set()
        self._spinner_frame: int = 0
        self._spinner_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-bar"):
            yield Input(
                placeholder="Describe the initiative and press Enter…",
                id="initiative-title",
            )
            yield Input(
                placeholder="Evidence source (scenario name or path; blank = sample)",
                id="evidence-source",
            )
        with Horizontal(id="lanes"):
            with VerticalScroll(id="left-lane"):
                yield Static("Waiting…", id="evidence-provenance", classes="panel")
                yield Static("Waiting…", id="recall", classes="panel")
            with Vertical(id="center-lane"):
                with Grid(id="analyst-grid"):
                    yield Static(
                        "Waiting…", id="customer_research", classes="panel analyst"
                    )
                    yield Static(
                        "Waiting…", id="product_analytics", classes="panel analyst"
                    )
                    yield Static("Waiting…", id="market", classes="panel analyst")
                    yield Static("Waiting…", id="business", classes="panel analyst")
                    yield Static("Waiting…", id="technical", classes="panel analyst")
                with VerticalScroll(id="debate-scroll"):
                    yield Static("Waiting…", id="debate")
            with Vertical(id="right-lane"):
                yield Static("Waiting…", id="strategist", classes="panel")
                yield Static("Waiting…", id="judgment", classes="panel")
                with VerticalScroll(id="risk-scroll"):
                    yield Static("Waiting…", id="risk")
                yield Static("Waiting…", id="governance", classes="panel")
        yield Static("", id="status-log", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(_THEME)
        self.theme = "productagents"
        for widget_id in _TITLES:
            if widget_id == "status-log":
                self.query_one("#status-log").border_title = _TITLES["status-log"]
            else:
                self._set_state(widget_id, "idle")
        if self._show_home:
            self._open_home()

    def _set_state(self, widget_id: str, state: str) -> None:
        try:
            widget = self.query_one(f"#{widget_id}")
        except NoMatches:
            return
        widget.remove_class("failed", "warning")
        if state == "failed":
            widget.add_class("failed")
        elif state == "warning":
            widget.add_class("warning")
        if state == "running":
            self._spinning.add(widget_id)
            self._ensure_spinner()
            self._paint_state(widget_id, _SPINNER_FRAMES[self._spinner_frame])
        else:
            self._spinning.discard(widget_id)
            self._paint_state(widget_id, _STATE_ICON[state])

    def _paint_state(self, widget_id: str, icon: str) -> None:
        try:
            widget = self.query_one(f"#{widget_id}")
        except NoMatches:
            return
        base = _TITLES.get(widget_id, widget_id)
        widget.border_title = f"{icon} {base}"

    def _ensure_spinner(self) -> None:
        if self._spinner_timer is None:
            self._spinner_timer = self.set_interval(0.12, self._advance_spinner)

    def _advance_spinner(self) -> None:
        if not self._spinning:
            return
        self._spinner_frame = (self._spinner_frame + 1) % len(_SPINNER_FRAMES)
        frame = _SPINNER_FRAMES[self._spinner_frame]
        for widget_id in self._spinning:
            self._paint_state(widget_id, frame)

    def _open_home(self) -> None:
        status = self._config_checker()
        self.push_screen(HomeScreen(status))
        if not status.ok:
            self.open_setup()

    def open_setup(self) -> None:
        self.push_screen(
            SetupScreen(self._config_checker(), writer=self._env_writer),
            self._after_setup,
        )

    def _after_setup(self, saved: bool | None) -> None:
        if saved and self._rebuild is not None:
            try:
                self._runner, self._reflector = self._rebuild()
                self._runner_error = None
            except Exception as exc:  # noqa: BLE001 - keep the menu usable
                self._runner, self._reflector = None, None
                self._runner_error = str(exc)
        screen = self.screen
        if isinstance(screen, HomeScreen):
            screen.refresh_status(self._config_checker())

    def start_decision(self) -> None:
        if isinstance(self.screen, HomeScreen):
            self.pop_screen()

    def action_home(self) -> None:
        if not isinstance(self.screen, HomeScreen):
            self._open_home()

    def on_input_submitted(self, message: Input.Submitted) -> None:
        if message.input.id != "initiative-title":
            return
        title = message.value.strip()
        if not title:
            return
        if self._runner is None:
            reason = self._runner_error or "model not configured"
            self._log_status(
                f"Cannot run — {reason}. Open the menu (ctrl+h) to fix your "
                "provider/key, or install the provider's integration package.",
                level="error",
            )
            return
        spec = self.query_one("#evidence-source", Input).value.strip()
        try:
            evidence = self._collector(spec) if spec else self._evidence
        except EvidenceError as exc:
            self._log_status(f"Evidence error: {exc}", level="error")
            return
        prov = "\n".join(f"• {ref.field} ← {ref.source}" for ref in evidence.sources)
        self.query_one("#evidence-provenance", Static).update(prov or "(default)")
        self._reset_panels()
        self._run(Initiative(title=title, description=title), evidence)

    def _reset_panels(self) -> None:
        """Clear every live panel back to its pre-run placeholder."""
        for node_id in _PANELS:
            self.query_one(f"#{node_id}", Static).update("…")
        self._debate_lines = []
        self._risk_lines = []
        self.query_one("#debate", Static).update("…")
        self.query_one("#risk", Static).update("…")
        self.query_one("#governance", Static).update("…")
        self.query_one("#judgment", Static).update("…")
        self._status_lines = []
        self.query_one("#status-log", Static).update("")
        for widget_id in _TITLES:
            if widget_id == "status-log":
                continue
            state = "waiting" if widget_id in _WAITING_AT_START else "idle"
            self._set_state(widget_id, state)

    def action_reflect(self) -> None:
        if self._reflector is None:
            return
        self.push_screen(
            ReflectionScreen(
                reflector=self._reflector,
                reader=self._reader,
                outcome_recorder=self._outcome_recorder,
            )
        )

    async def _ask_human(self, advisory):
        """Pause for a human governance decision; returns a HumanDecision."""
        return await self.push_screen_wait(ApprovalScreen(advisory))

    @work(exclusive=True)
    async def _run(self, initiative: Initiative, evidence) -> None:
        if self._runner is None:
            return
        handlers = {
            ProgressEvent: self._on_progress,
            NodeCompleteEvent: self._on_node_complete,
            NodeErrorEvent: self._on_node_error,
            DebateTurnEvent: self._on_debate_turn,
            RiskAssessmentEvent: self._on_risk_assessment,
            JudgmentEvent: self._on_judgment,
            GovernanceVerdictEvent: self._on_governance_verdict,
            FinalVerdictEvent: self._on_final_verdict,
            RecallEvent: self._on_recall,
            FinishedEvent: self._on_finished,
        }
        finished: FinishedEvent | None = None
        portfolio = self._reader()
        outcomes = self._outcome_reader()
        try:
            async for event in self._runner(
                initiative,
                evidence,
                portfolio=portfolio,
                outcomes=outcomes,
                approver=self._ask_human,
            ):
                handler = handlers.get(type(event))
                if handler is not None:
                    handler(event)
                if isinstance(event, FinishedEvent):
                    finished = event
        except Exception as exc:  # noqa: BLE001 - never crash the worker
            self._log_status(f"run failed: {exc}", level="error")
            return

        if finished is None or finished.recommendation is None:
            return
        if not finished.recommendation.failed:
            self._record(initiative, evidence, finished)
            return
        await self._handle_degraded(initiative, evidence, finished)

    def _record(self, initiative, evidence, finished, *, governance=None) -> None:
        self._recorder(
            DecisionRecord(
                initiative=initiative,
                recommendation=finished.recommendation,
                reports=finished.reports,
                debate=finished.debate,
                risks=finished.risks,
                governance=governance
                if governance is not None
                else finished.governance,
                judgment=finished.judgment,
                prior_lessons=finished.prior_lessons,
                evidence_sources=evidence.sources,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

    async def _handle_degraded(self, initiative, evidence, finished) -> None:
        choice = await self.push_screen_wait(DegradedRunScreen())
        if choice == "retry":
            self._reset_panels()
            self._run(initiative, evidence)
        elif choice == "decide":
            decision = await self._ask_human(None)
            governance = GovernanceVerdict(
                verdict=decision.verdict,
                rationale=decision.rationale,
                decided_by="human",
            )
            self._record(initiative, evidence, finished, governance=governance)
        # "quit" or dismissed: record nothing, leave the failed panels in place.

    def _on_progress(self, event) -> None:
        if event.node in _PANELS:
            self.query_one(f"#{event.node}", Static).update(f"… {event.message}")
            if event.node == "strategist":
                self._set_state("debate-scroll", "done")
            self._set_state(event.node, "running")

    def _on_node_complete(self, event) -> None:
        if event.node not in _PANELS:
            return
        report = event.report
        if report.failed:
            self.query_one(f"#{event.node}", Static).update(
                "[red]failed — see Status / Errors below[/red]"
            )
            self._set_state(event.node, "failed")
        else:
            body = "\n".join(f"• {f}" for f in report.findings) or "(no findings)"
            self.query_one(f"#{event.node}", Static).update(body)
            self._set_state(event.node, "done")

    def _on_node_error(self, event) -> None:
        label = _TITLES.get(_WIDGET_FOR_NODE.get(event.node, event.node), event.node)
        self._log_status(f"{label}: {event.message}", level="error")
        self._mark_failed(event.node)

    def _on_debate_turn(self, event) -> None:
        self._debate_lines.append(
            f"[{event.side} · round {event.round}] {event.argument}"
        )
        self.query_one("#debate", Static).update("\n\n".join(self._debate_lines))
        self._set_state("debate-scroll", "running")

    def _on_risk_assessment(self, event) -> None:
        self._risk_lines.append(f"[{event.role} · {event.level}] {event.rationale}")
        self.query_one("#risk", Static).update("\n\n".join(self._risk_lines))
        self._set_state("risk-scroll", "running")

    def _on_judgment(self, event) -> None:
        status = "PASS" if event.passed else "FAIL"
        self.query_one("#judgment", Static).update(
            f"[b]{status}[/b] (attempt {event.attempt})\n\n"
            f"Evidence: {event.evidence_grounding_score:.0%}  "
            f"Coherence: {event.rationale_coherence_score:.0%}\n\n"
            f"{event.critique}"
        )
        self._set_state("strategist", "done")
        self._set_state("judgment", "done" if event.passed else "warning")

    def _on_governance_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            f"[b]{event.verdict}[/b]\n\n{event.rationale}"
        )
        self._set_state("risk-scroll", "done")
        state = "done" if event.verdict == "approve" else "warning"
        self._set_state("governance", state)

    def _on_final_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            f"[b]FINAL ({event.decided_by}): {event.verdict}[/b]\n\n{event.rationale}"
        )
        state = "done" if event.verdict == "approve" else "warning"
        self._set_state("governance", state)

    def _on_recall(self, event) -> None:
        body = "\n".join(f"• {line}" for line in event.lessons) or (
            "(no relevant past lessons)"
        )
        self.query_one("#recall", Static).update(body)
        self._set_state("recall", "done")

    def _on_finished(self, event) -> None:
        rec = event.recommendation
        if rec is None:
            return
        if rec.failed:
            self.query_one("#strategist", Static).update(
                "[red]failed — could not synthesize a recommendation. "
                "See Status / Errors below.[/red]"
            )
            self._set_state("strategist", "failed")
            return
        self._render_recommendation(rec)
        self._set_state("strategist", "done")

    def _render_recommendation(self, recommendation) -> None:
        text = (
            f"[b]{recommendation.recommendation}[/b]\n\n"
            f"Confidence: {recommendation.confidence:.0%}\n\n"
            f"{recommendation.rationale}\n\n"
            "Expected outcomes:\n"
            + "\n".join(f"• {o}" for o in recommendation.expected_outcomes)
        )
        self.query_one("#strategist", Static).update(text)

    def _log_status(self, message: str, *, level: str = "info") -> None:
        ts = datetime.now(UTC).strftime("%H:%M:%S")
        icon = "✗" if level == "error" else "·"
        color = "red" if level == "error" else "dim"
        self._status_lines.append(f"[{color}]{icon} {ts} {message}[/{color}]")
        self._status_lines = self._status_lines[-50:]
        self.query_one("#status-log", Static).update("\n".join(self._status_lines))

    def _mark_failed(self, node: str) -> None:
        widget_id = _WIDGET_FOR_NODE.get(node, node)
        self._set_state(widget_id, "failed")


def _build_app() -> ProductAgentsApp:
    def rebuild():
        model = get_model()
        graph = build_graph(model, human_in_the_loop=True)
        return partial(run_decision, graph), partial(reflect, model=model)

    try:
        runner, reflector = rebuild()
        build_error = None
    except Exception as exc:  # noqa: BLE001 - launch into setup instead of crashing
        runner, reflector = None, None
        build_error = str(exc)
    evidence = load_scenario("sample")
    return ProductAgentsApp(
        runner,
        evidence,
        reflector=reflector,
        rebuild=rebuild,
        runner_error=build_error,
    )


def main() -> None:
    load_env()
    configure_logging()
    app = _build_app()
    app.run()
