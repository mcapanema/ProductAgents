"""Textual TUI for running a ProductAgents decision and showing it live."""

import pathlib
from datetime import UTC, datetime
from functools import partial
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Label, Static

from productagents.agents.evidence import EvidenceError, collect_evidence, load_scenario
from productagents.agents.llm import get_model
from productagents.agents.reflection import reflect
from productagents.agents.runner import (
    DebateTurnEvent,
    FinalVerdictEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    JudgmentEvent,
    NodeCompleteEvent,
    NodeErrorEvent,
    ProgressEvent,
    RecallEvent,
    RecommendationEvent,
    RiskAssessmentEvent,
    RunAbortedEvent,
)
from productagents.app.decision_context import (
    make_decision_reader,
    make_decision_runner,
    make_outcome_recorder,
    make_recorder,
)
from productagents.app.setup import check_config, write_env
from productagents.app.sync import (
    check_connector_health,
    describe_health,
    describe_plan,
    describe_report,
    run_connector_sync,
    static_connector_plan,
)
from productagents.app.tui._constants import (
    ANALYST_IDS as _ANALYST_IDS,
)
from productagents.app.tui._constants import (
    PANELS as _PANELS,
)
from productagents.app.tui._constants import (
    THEME as _THEME,
)
from productagents.app.tui._constants import (
    TITLES as _TITLES,
)
from productagents.app.tui._constants import (
    WAITING_AT_START as _WAITING_AT_START,
)
from productagents.app.tui._constants import (
    WIDGET_FOR_NODE as _WIDGET_FOR_NODE,
)
from productagents.app.tui._format import (
    format_debate_turn,
    format_governance,
    format_judgment,
    format_recommendation,
    format_risk_line,
)
from productagents.app.tui._format import format_recall_body as _format_recall_body
from productagents.app.tui._indicator import PanelIndicator
from productagents.app.tui.approval import ApprovalScreen
from productagents.app.tui.degraded import DegradedRunScreen
from productagents.app.tui.home_screen import HomeScreen
from productagents.app.tui.rail import PipelineRail
from productagents.app.tui.reflection import ReflectionScreen
from productagents.app.tui.setup_screen import SetupScreen
from productagents.core.config import load_env
from productagents.core.logging_config import configure_logging
from productagents.core.models import DecisionRecord, GovernanceVerdict, Initiative


class ProductAgentsApp(App):
    DEFAULT_CSS = ""
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
        recorder=None,
        reader=None,
        reflector=None,
        outcome_recorder=None,
        config_checker=check_config,
        env_writer=write_env,
        connector_syncer=run_connector_sync,
        connector_health_checker=check_connector_health,
        connector_planner=static_connector_plan,
        rebuild=None,
        show_home=True,
        runner_error=None,
    ):
        # Store custom theme as instance variable before calling super().__init__()
        # so it can be accessed when CSS is parsed. We'll set it as active in
        # _setup_mode which is called before CSS parsing.
        super().__init__()
        self._runner = runner
        self._runner_error = runner_error
        self._evidence = evidence
        self._collector = collector
        self._recorder = recorder
        self._reader = reader
        self._reflector = reflector
        self._outcome_recorder = outcome_recorder
        self._config_checker = config_checker
        self._env_writer = env_writer
        self._connector_syncer = connector_syncer
        self._connector_health_checker = connector_health_checker
        self._connector_planner = connector_planner
        self._rebuild = rebuild
        self._show_home = show_home
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []
        self._status_lines: list[str] = []
        self._indicator = PanelIndicator(self)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-bar"):
            with Vertical(id="initiative-field"):
                yield Label("Initiative — press Enter to run", id="initiative-label")
                yield Input(
                    placeholder="Describe the initiative…",
                    id="initiative-title",
                )
            with Vertical(id="evidence-field"):
                yield Label(
                    "Evidence  (scenario or path · blank = sample)", id="evidence-label"
                )
                yield Input(
                    placeholder="sample",
                    id="evidence-source",
                )
        yield PipelineRail()
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
        # Register and activate the theme before loading stylesheet so its custom
        # variables ($stage-evidence, etc.) are defined when app.tcss is parsed.
        self.register_theme(_THEME)
        self.theme = "productagents"
        # Publish the active theme's variables via the public API
        # (replaces the old poke into stylesheet._variables).
        self.stylesheet.set_variables(self.get_css_variables())
        # Load stylesheet after the theme is active so $stage-* variables resolve.
        # ponytail: explicit load kept because Textual resolves CSS_PATH variables
        # before on_mount fires; upgrade to CSS_PATH if Textual adds a post-mount hook.
        css_file = pathlib.Path(__file__).parent / "app.tcss"
        self.stylesheet.add_source(css_file.read_text(), read_from=(str(css_file), ""))
        for widget_id in _TITLES:
            if widget_id == "status-log":
                self.query_one("#status-log").border_title = _TITLES["status-log"]
            else:
                self._set_state(widget_id, "idle")
        if self._show_home:
            self._open_home()
        if not self._show_home:
            self.query_one("#initiative-title", Input).focus()

    def _rail(self) -> PipelineRail:
        return self.query_one("#pipeline-rail", PipelineRail)

    def _completed_analysts(self) -> int:
        return sum(
            1
            for node_id in _ANALYST_IDS
            if str(self.query_one(f"#{node_id}").border_title).startswith("✓")
        )

    def _set_state(self, widget_id: str, state: str) -> None:
        self._indicator.set_state(widget_id, state)

    def _open_home(self) -> None:
        status = self._config_checker()
        line = describe_plan(self._connector_planner())
        self.push_screen(HomeScreen(status, line))
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
        self.query_one("#initiative-title", Input).focus()

    @work(exclusive=True)
    async def sync_sources(self) -> None:
        """Run a connector sync, then show the outcome on the home menu."""
        try:
            report = await self._connector_syncer()
        except Exception as exc:  # noqa: BLE001 - degrade visibly, never crash
            self._log_status(f"sync failed: {exc}", level="error")
            return
        line = describe_report(report)
        self._log_status(f"sync: {line}")
        screen = self.screen
        if isinstance(screen, HomeScreen):
            screen.refresh_connectors(line)

    @work(exclusive=True)
    async def check_health(self) -> None:
        """Probe connector health, then show the outcome on the home menu."""
        try:
            report = await self._connector_health_checker()
        except Exception as exc:  # noqa: BLE001 - degrade visibly, never crash
            self._log_status(f"health check failed: {exc}", level="error")
            return
        line = describe_health(report)
        self._log_status(f"health: {line}")
        screen = self.screen
        if isinstance(screen, HomeScreen):
            screen.refresh_connectors(line)

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
        self._rail().set_stage("evidence", "done")
        self._rail().set_stage("analysis", "running")
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
        self.query_one("#status-log").remove_class("-has-error")
        for widget_id in _TITLES:
            if widget_id == "status-log":
                continue
            state = "waiting" if widget_id in _WAITING_AT_START else "idle"
            self._set_state(widget_id, state)
        self._rail().reset()

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
            RunAbortedEvent: self._on_run_aborted,
            DebateTurnEvent: self._on_debate_turn,
            RiskAssessmentEvent: self._on_risk_assessment,
            JudgmentEvent: self._on_judgment,
            GovernanceVerdictEvent: self._on_governance_verdict,
            FinalVerdictEvent: self._on_final_verdict,
            RecallEvent: self._on_recall,
            RecommendationEvent: self._on_recommendation,
            FinishedEvent: self._on_finished,
        }
        finished: FinishedEvent | None = None
        try:
            async for event in self._runner(
                initiative,
                evidence,
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
            try:
                await self._record(initiative, evidence, finished)
            except Exception as exc:  # noqa: BLE001 - degrade visibly, never crash
                self._log_status(f"failed to save decision: {exc}", level="error")
            return
        await self._handle_degraded(initiative, evidence, finished)

    async def _record(self, initiative, evidence, finished, *, governance=None) -> None:
        if self._recorder is None:
            return
        await self._recorder(
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
            try:
                await self._record(
                    initiative, evidence, finished, governance=governance
                )
            except Exception as exc:  # noqa: BLE001 - degrade visibly, never crash
                self._log_status(f"failed to save decision: {exc}", level="error")
        # "quit" or dismissed: record nothing, leave the failed panels in place.

    def _on_progress(self, event) -> None:
        if event.node in _PANELS:
            self.query_one(f"#{event.node}", Static).update(f"… {event.message}")
            if event.node == "strategist":
                self._set_state("debate-scroll", "done")
                self._rail().set_stage("debate", "done")
                self._rail().set_stage("strategy", "running")
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
            if event.node in _ANALYST_IDS:
                rail = self._rail()
                rail.bump_analyst()
                if self._completed_analysts() >= len(_ANALYST_IDS):
                    rail.set_stage("analysis", "done")

    def _on_node_error(self, event) -> None:
        label = _TITLES.get(_WIDGET_FOR_NODE.get(event.node, event.node), event.node)
        self._log_status(f"{label}: {event.message}", level="error")
        self._mark_failed(event.node)

    def _on_run_aborted(self, event) -> None:
        self._log_status(f"run aborted — {event.message}", level="error")
        if event.node:
            self._mark_failed(event.node)

    def _on_debate_turn(self, event) -> None:
        self._debate_lines.append(
            format_debate_turn(event.side, event.round, event.argument)
        )
        self.query_one("#debate", Static).update("\n\n".join(self._debate_lines))
        self._set_state("debate-scroll", "running")
        self._rail().set_stage("analysis", "done")
        self._rail().set_stage("debate", "running")

    def _on_risk_assessment(self, event) -> None:
        self._risk_lines.append(
            format_risk_line(event.role, event.level, event.rationale)
        )
        self.query_one("#risk", Static).update("\n\n".join(self._risk_lines))
        self._set_state("risk-scroll", "running")
        self._rail().set_stage("risk", "running")

    def _on_judgment(self, event) -> None:
        self.query_one("#judgment", Static).update(
            format_judgment(
                event.passed,
                event.attempt,
                event.evidence_grounding_score,
                event.rationale_coherence_score,
                event.critique,
            )
        )
        self._set_state("strategist", "done")
        self._set_state("judgment", "done" if event.passed else "warning")
        self._rail().set_stage("strategy", "done")
        self._rail().set_stage("judge", "done" if event.passed else "warning")
        self._rail().set_stage("risk", "running")

    def _on_governance_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            format_governance(event.verdict, event.rationale)
        )
        self._set_state("risk-scroll", "done")
        state = "done" if event.verdict == "approve" else "warning"
        self._set_state("governance", state)
        self._rail().set_stage("risk", "done")
        self._rail().set_stage(
            "governance", "done" if event.verdict == "approve" else "warning"
        )

    def _on_final_verdict(self, event) -> None:
        self.query_one("#governance", Static).update(
            format_governance(
                event.verdict, event.rationale, decided_by=event.decided_by
            )
        )
        state = "done" if event.verdict == "approve" else "warning"
        self._set_state("governance", state)
        self._rail().set_stage(
            "governance", "done" if event.verdict == "approve" else "warning"
        )

    def _on_recall(self, event) -> None:
        self.query_one("#recall", Static).update(_format_recall_body(event.lessons))
        self._set_state("recall", "done")

    def _on_recommendation(self, event) -> None:
        self._render_strategist_result(event.recommendation)

    def _on_finished(self, event) -> None:
        if event.recommendation is not None:
            self._render_strategist_result(event.recommendation)

    def _render_strategist_result(self, rec) -> None:
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
        self.query_one("#strategist", Static).update(
            format_recommendation(recommendation)
        )

    def _log_status(self, message: str, *, level: str = "info") -> None:
        ts = datetime.now(UTC).strftime("%H:%M:%S")
        icon = "✗" if level == "error" else "·"
        color = "red" if level == "error" else "dim"
        self._status_lines.append(f"[{color}]{icon} {ts} {message}[/{color}]")
        self._status_lines = self._status_lines[-50:]
        self.query_one("#status-log", Static).update("\n".join(self._status_lines))
        if level == "error":
            self.query_one("#status-log").add_class("-has-error")

    def _mark_failed(self, node: str) -> None:
        widget_id = _WIDGET_FOR_NODE.get(node, node)
        self._set_state(widget_id, "failed")


def _build_app() -> ProductAgentsApp:
    def rebuild():
        model = get_model()
        runner = make_decision_runner(model, human_in_the_loop=True)
        return runner, partial(reflect, model=model)

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
        recorder=make_recorder(),
        reader=make_decision_reader(),
        outcome_recorder=make_outcome_recorder(),
        reflector=reflector,
        rebuild=rebuild,
        runner_error=build_error,
    )


def main() -> None:
    load_env()
    configure_logging()
    app = _build_app()
    app.run()
