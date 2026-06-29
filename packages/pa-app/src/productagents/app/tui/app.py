"""Textual TUI for running a ProductAgents decision and showing it live."""

import pathlib
from datetime import UTC, datetime
from functools import partial
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Label, Static

from productagents.app.setup import check_config, write_env
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
from productagents.app.tui._indicator import PanelIndicator
from productagents.app.tui.approval import ApprovalScreen
from productagents.app.tui.degraded import DegradedRunScreen
from productagents.app.tui.home_screen import HomeScreen
from productagents.app.tui.presenter import PipelinePresenter
from productagents.app.tui.rail import PipelineRail
from productagents.app.tui.reflection import ReflectionScreen
from productagents.app.tui.setup_screen import SetupScreen
from productagents.core.config import env_int
from productagents.core.models import (
    DecisionRecord,
    GovernanceVerdict,
    Initiative,
    Recommendation,
)
from productagents.platform import events as ev
from productagents.platform.connectors import (
    check_connector_health,
    describe_health,
    describe_plan,
    describe_report,
    run_connector_sync,
    static_connector_plan,
)
from productagents.platform.context import (
    make_decision_reader,
    make_outcome_recorder,
    make_recorder,
)
from productagents.platform.evidence import (
    EvidenceError,
    collect_evidence,
    load_scenario,
)
from productagents.platform.llm import get_model
from productagents.platform.reflection import reflect
from productagents.platform.workflow import WorkflowService
from productagents.platform.workspace import DEFAULT_WORKSPACE


class ProductAgentsApp(App):
    DEFAULT_CSS = ""
    TITLE = "ProductAgents"
    BINDINGS: ClassVar[list] = [
        ("ctrl+r", "reflect", "Reflect on a decision"),
        ("ctrl+h", "home", "Menu"),
    ]

    def __init__(
        self,
        workflow_service,
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
        workspace_name=DEFAULT_WORKSPACE,
        runner_error=None,
    ):
        # Store custom theme as instance variable before calling super().__init__()
        # so it can be accessed when CSS is parsed. We'll set it as active in
        # _setup_mode which is called before CSS parsing.
        super().__init__()
        self._workflow_service = workflow_service
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
        self._workspace_name = workspace_name
        self._debate_lines: list[str] = []
        self._risk_lines: list[str] = []
        self._status_lines: list[str] = []
        self._indicator = PanelIndicator(self)
        self._presenter = PipelinePresenter(self)
        self._sync_timer = None

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
        interval = env_int("PRODUCTAGENTS_SYNC_INTERVAL", 0, minimum=0)
        if interval > 0:
            # ponytail: Textual's own timer IS the in-process scheduler — no thread,
            # auto-cancelled on exit. Reuses the same worker as the manual button.
            self._sync_timer = self.set_interval(interval, self.sync_sources)

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
        self.push_screen(HomeScreen(status, line, workspace_name=self._workspace_name))
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
                self._workflow_service, self._reflector = self._rebuild()
                self._runner_error = None
            except Exception as exc:  # noqa: BLE001 - keep the menu usable
                self._workflow_service, self._reflector = None, None
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
        if self._workflow_service is None:
            reason = self._runner_error or "model not configured"
            self._log_status(
                f"Cannot run — {reason}. Open the menu (ctrl+h) to fix your "
                "provider/key, or install the provider's integration package.",
                level="error",
            )
            return
        spec = self.query_one("#evidence-source", Input).value.strip()
        try:
            # Resolve for the provenance panel only; the DecisionService resolves
            # the spec again internally.
            # ponytail: resolved twice, harmless for local; unify via an
            # EvidenceService later.
            evidence = self._collector(spec) if spec else self._evidence
        except EvidenceError as exc:
            self._log_status(f"Evidence error: {exc}", level="error")
            return
        prov = "\n".join(f"• {ref.field} ← {ref.source}" for ref in evidence.sources)
        self.query_one("#evidence-provenance", Static).update(prov or "(default)")
        self._reset_panels()
        self._rail().set_stage("evidence", "done")
        self._rail().set_stage("analysis", "running")
        self._run(Initiative(title=title, description=title), spec, evidence)

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

    async def _ask_human(self, request=None):
        """Pause for a human governance decision; returns a HumanDecision.

        ``request`` is an ``ev.ApprovalRequested`` (from a HITL run) or ``None``
        (the degraded "decide" path, where there is no advisory verdict).
        """
        advisory = (
            GovernanceVerdict(
                verdict=request.advisory_verdict,
                rationale=request.advisory_rationale,
            )
            if request is not None
            else None
        )
        return await self.push_screen_wait(ApprovalScreen(advisory))

    @work(exclusive=True)
    async def _run(self, initiative: Initiative, evidence_spec: str, evidence) -> None:
        if self._workflow_service is None:
            return
        finished: ev.SessionFinished | None = None
        aborted = False
        try:
            _session, stream = self._workflow_service.run(
                "evaluate_initiative",
                initiative,
                evidence_spec,
                approver=self._ask_human,
            )
            async for event in stream:
                self._presenter.dispatch(event)
                if isinstance(event, ev.SessionFinished):
                    finished = event
                elif isinstance(event, ev.SessionFailed):
                    aborted = True
        except Exception as exc:  # noqa: BLE001 - never crash the worker
            self._log_status(f"run failed: {exc}", level="error")
            return

        # The DecisionService already recorded a healthy run. The TUI only steps
        # in for the degraded paths: a fatal abort, or a finished-but-failed run.
        if aborted:
            await self._handle_degraded(initiative, evidence_spec, evidence, None)
            return
        if finished is None:
            return
        if finished.recommendation is not None and finished.recommendation.failed:
            await self._handle_degraded(initiative, evidence_spec, evidence, finished)

    async def _record(self, initiative, evidence, finished, *, governance) -> None:
        """Persist a human-decided record for a degraded run (TUI-owned path).

        ``finished`` is an ``ev.SessionFinished`` (failed recommendation) or
        ``None`` (fatal abort, no payload — record a minimal placeholder).
        """
        if self._recorder is None:
            return
        if finished is not None:
            record = DecisionRecord(
                initiative=initiative,
                recommendation=finished.recommendation,
                reports=finished.reports,
                debate=finished.debate,
                risks=finished.risks,
                governance=governance,
                judgment=finished.judgment,
                prior_lessons=finished.prior_lessons,
                evidence_sources=evidence.sources,
                timestamp=datetime.now(UTC).isoformat(),
            )
        else:
            record = DecisionRecord(
                initiative=initiative,
                recommendation=Recommendation(
                    recommendation="Run aborted before a recommendation was produced.",
                    confidence=0.0,
                    rationale="The decision run failed; a human made the call.",
                    expected_outcomes=[],
                    failed=True,
                ),
                reports=[],
                governance=governance,
                evidence_sources=evidence.sources,
                timestamp=datetime.now(UTC).isoformat(),
            )
        await self._recorder(record)

    async def _handle_degraded(
        self, initiative, evidence_spec, evidence, finished
    ) -> None:
        choice = await self.push_screen_wait(DegradedRunScreen())
        if choice == "retry":
            self._reset_panels()
            self._run(initiative, evidence_spec, evidence)
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


def _build_app(*, workspace_name: str = DEFAULT_WORKSPACE) -> ProductAgentsApp:
    def rebuild():
        model = get_model()
        service = WorkflowService.for_model(
            model, recorder=make_recorder(), human_in_the_loop=True
        )
        return service, partial(reflect, model=model)

    try:
        service, reflector = rebuild()
        build_error = None
    except Exception as exc:  # noqa: BLE001 - launch into setup instead of crashing
        service, reflector = None, None
        build_error = str(exc)
    evidence = load_scenario("sample")
    return ProductAgentsApp(
        service,
        evidence,
        recorder=make_recorder(),
        reader=make_decision_reader(),
        outcome_recorder=make_outcome_recorder(),
        reflector=reflector,
        rebuild=rebuild,
        workspace_name=workspace_name,
        runner_error=build_error,
    )


def launch_tui(workspace_name: str) -> None:
    """Build the Textual app for ``workspace_name`` and run it (the CLI's
    no-subcommand path)."""
    app = _build_app(workspace_name=workspace_name)
    app.run()
