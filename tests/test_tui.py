from functools import partial

from textual.widgets import Button, Input, Label

from productagents.agents.graph import build_graph
from productagents.agents.runner import (
    DebateTurnEvent,
    FinalVerdictEvent,
    FinishedEvent,
    GovernanceVerdictEvent,
    JudgmentEvent,
    ProgressEvent,
    RiskAssessmentEvent,
    run_decision,
)
from productagents.app.setup import ConfigStatus
from productagents.app.tui.app import ProductAgentsApp
from productagents.app.tui.degraded import DegradedRunScreen
from productagents.app.tui.home_screen import HomeScreen
from productagents.app.tui.setup_screen import SetupScreen
from productagents.core.models import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    HumanDecision,
    Initiative,
    JudgeFinding,
    Recommendation,
    RiskFinding,
)
from tests.fakes import FakeChatModel


def _runner_and_evidence():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: Recommendation(
                recommendation="Build SSO now",
                confidence=0.81,
                rationale="strong demand",
                expected_outcomes=["enterprise unblock"],
            ),
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="ok",
            ),
            RiskFinding: RiskFinding(level="medium", rationale="some delivery risk"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="best use of resources"
            ),
        }
    )
    graph = build_graph(model)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    return partial(run_decision, graph), evidence


async def test_app_renders_recommendation_records_debate_and_risk(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    runner, evidence = _runner_and_evidence()
    recorded = []

    def recorder(record):
        recorded.append(record)

    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=recorder,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        debate_text = str(pilot.app.query_one("#debate").content)
        risk_text = str(pilot.app.query_one("#risk").content)
        gov_text = str(pilot.app.query_one("#governance").content)
        strat_text = str(pilot.app.query_one("#strategist").content)
        assert "an argument" in debate_text
        assert "advocate" in debate_text
        assert "Delivery Risk Reviewer" in risk_text
        assert "medium" in risk_text
        assert "approve" in gov_text
        assert "Build SSO now" in strat_text

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO now"
    assert len(recorded[0].debate) == 4
    assert len(recorded[0].risks) == 5
    assert recorded[0].governance.verdict == "approve"
    assert recorded[0].risks[0].reviewer == "delivery"


async def test_app_renders_new_analyst_panels(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        market_text = str(pilot.app.query_one("#market").content)
        business_text = str(pilot.app.query_one("#business").content)
        technical_text = str(pilot.app.query_one("#technical").content)

    assert "demand" in market_text
    assert "demand" in business_text
    assert "demand" in technical_text


def test_format_recall_body_lists_lessons():
    from productagents.app.tui.app import _format_recall_body

    body = _format_recall_body(["lesson one", "lesson two"])

    assert "• lesson one" in body
    assert "• lesson two" in body


def test_format_recall_body_empty_state_points_to_reflection():
    from productagents.app.tui.app import _format_recall_body

    body = _format_recall_body([])

    # Empty state must guide the user toward building memory via reflection.
    assert "ctrl+r" in body
    assert "no relevant past lessons" not in body.lower()


async def test_set_state_drives_idle_active_done_classes():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app._set_state("market", "idle")
        assert app.query_one("#market").has_class("-idle")
        app._set_state("market", "running")
        assert app.query_one("#market").has_class("-active")
        assert not app.query_one("#market").has_class("-idle")
        app._set_state("market", "done")
        assert app.query_one("#market").has_class("-done")
        assert not app.query_one("#market").has_class("-active")


async def test_initiative_input_is_focused_on_decision_screen():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert pilot.app.focused is pilot.app.query_one("#initiative-title")
        # Both fields are labelled.
        init_label = pilot.app.query_one("#initiative-label", Label)
        assert "Initiative" in str(init_label.content)
        evid_label = pilot.app.query_one("#evidence-label", Label)
        assert "Evidence" in str(evid_label.content)


async def test_app_renders_recalled_lessons(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.core.models import (
        DecisionRecord,
        Initiative,
        OutcomeRecord,
        Recommendation,
    )

    runner, evidence = _runner_and_evidence()

    prior = DecisionRecord(
        decision_id="d1",
        initiative=Initiative(title="Add enterprise SSO login", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )
    outcome = OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["shipped late"],
        prediction_accuracy=0.5,
        lessons_learned=["SSO integrations take longer than predicted"],
        reflected_at="2026-06-20T00:00:00+00:00",
    )

    recorded = []
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=recorded.append,
        reader=lambda: [prior],
        outcome_reader=lambda: [outcome],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        recall_text = str(pilot.app.query_one("#recall").content)

    assert "take longer than predicted" in recall_text
    assert len(recorded) == 1
    assert any(
        "take longer than predicted" in line for line in recorded[0].prior_lessons
    )


async def test_app_collects_evidence_from_typed_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, default_evidence = _runner_and_evidence()

    folder = tmp_path / "typed-dir"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("typed-dir feedback")
    (folder / "product_analytics.json").write_text('{"dau": 9}')

    seen = {}

    async def capturing_runner(initiative, evidence, **kwargs):
        seen["scenario"] = evidence.scenario
        async for event in runner(initiative, evidence, **kwargs):
            yield event

    from productagents.agents.evidence import collect_evidence

    app = ProductAgentsApp(
        capturing_runner,
        default_evidence,
        collector=collect_evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#evidence-source").value = str(folder)
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()

    assert seen["scenario"] == "typed-dir"


async def test_app_shows_error_for_bad_evidence_source(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, default_evidence = _runner_and_evidence()
    ran = {"called": False}

    async def tracking_runner(initiative, evidence, **kwargs):
        ran["called"] = True
        async for event in runner(initiative, evidence, **kwargs):
            yield event

    from productagents.agents.evidence import collect_evidence

    app = ProductAgentsApp(
        tracking_runner,
        default_evidence,
        collector=collect_evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#evidence-source").value = "/no/such/source/xyz"
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.pause()
        status_text = str(pilot.app.query_one("#status-log").content)

    assert ran["called"] is False
    assert "Evidence" in status_text or "evidence" in status_text


async def test_app_surfaces_runner_unavailable(monkeypatch):
    # When the model/graph could not be built (e.g. a provider package is
    # missing), runner is None. Submitting an initiative must tell the user
    # why instead of silently doing nothing.
    _, default_evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        None,
        default_evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
        runner_error="ImportError: requires the langchain-google-genai package",
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.pause()
        status_text = str(pilot.app.query_one("#status-log").content)

    assert "langchain-google-genai" in status_text


async def test_app_renders_and_records_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, default_evidence = _runner_and_evidence()

    folder = tmp_path / "prov-dir"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("prov feedback")
    (folder / "product_analytics.json").write_text('{"dau": 3}')

    from productagents.agents.evidence import collect_evidence

    recorded = []
    app = ProductAgentsApp(
        runner,
        default_evidence,
        collector=collect_evidence,
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#evidence-source").value = str(folder)
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        prov_text = str(pilot.app.query_one("#evidence-provenance").content)

    assert "customer_feedback" in prov_text
    assert "directory:" in prov_text
    assert len(recorded) == 1
    assert any(ref.field == "customer_feedback" for ref in recorded[0].evidence_sources)


async def test_completion_event_without_panel_is_ignored(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.agents.runner import FinishedEvent, NodeCompleteEvent
    from productagents.core.models import AnalystReport, Evidence, Recommendation

    async def fake_runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        # A completion event for a node id that has no matching panel must be
        # skipped, not crash the worker with NoMatches before the run finishes.
        yield NodeCompleteEvent(
            node="aggregator",
            report=AnalystReport(
                analyst="aggregator",
                role="Aggregator",
                findings=["x"],
                signals=[],
            ),
        )
        yield FinishedEvent(
            recommendation=Recommendation(
                recommendation="Build it",
                confidence=0.5,
                rationale="r",
                expected_outcomes=["o"],
            ),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
        )

    evidence = Evidence(
        scenario="sample", customer_feedback="d", product_analytics={"x": 1}
    )
    app = ProductAgentsApp(
        fake_runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        strat_text = str(pilot.app.query_one("#strategist").content)

    # The unknown-node completion was skipped, so the run reached FinishedEvent
    # and rendered the recommendation.
    assert "Build it" in strat_text


def _ok_status():
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=True,
    )


def _missing_status():
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=False,
        problems=["Missing API key: set ANTHROPIC_API_KEY for provider 'anthropic'."],
    )


async def test_app_shows_home_menu_when_config_ready():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=_ok_status,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
        assert app.screen.query_one("#home-run", Button).disabled is False


async def test_app_auto_opens_setup_when_config_incomplete():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=_missing_status,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, SetupScreen)


async def test_app_run_from_menu_reveals_decision_ui():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=_ok_status,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home-run")
        await pilot.pause()
        assert not isinstance(app.screen, HomeScreen)
        # The decision input is now on the active screen.
        app.query_one("#initiative-title")


async def test_setup_save_rebuilds_runner_and_refreshes_home():
    runner, evidence = _runner_and_evidence()
    state = {"ok": False}

    def checker():
        return _ok_status() if state["ok"] else _missing_status()

    written = {}

    def writer(values, **_kwargs):
        written.update(values)
        state["ok"] = True

    rebuilt = []

    def rebuild():
        rebuilt.append(True)
        return runner, None

    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=checker,
        env_writer=writer,
        rebuild=rebuild,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        # Incomplete config auto-opened the setup screen.
        assert isinstance(app.screen, SetupScreen)
        app.screen.query_one("#setup-key").value = "sk-test"
        await pilot.click("#setup-save")
        await pilot.pause()
        # Back on the home menu, now reporting Ready with run enabled.
        assert isinstance(app.screen, HomeScreen)
        assert app.screen.query_one("#home-run", Button).disabled is False

    assert written["ANTHROPIC_API_KEY"] == "sk-test"
    assert rebuilt == [True]


async def test_ctrl_h_reopens_menu_from_decision_ui():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        config_checker=_ok_status,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home-run")  # reveal decision UI
        await pilot.pause()
        await pilot.press("ctrl+h")  # back to the menu
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)


async def test_app_logs_node_error_and_marks_panel_failed():
    from productagents.agents.runner import FinishedEvent, NodeErrorEvent
    from productagents.core.models import Evidence, Recommendation

    async def fake_runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        yield NodeErrorEvent(node="technical", message="429 rate limit reached")
        yield FinishedEvent(
            recommendation=Recommendation(
                recommendation="Build it",
                confidence=0.5,
                rationale="r",
                expected_outcomes=["o"],
            ),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
        )

    evidence = Evidence(
        scenario="sample", customer_feedback="d", product_analytics={"x": 1}
    )
    app = ProductAgentsApp(
        fake_runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        status_text = str(pilot.app.query_one("#status-log").content)
        assert "429 rate limit reached" in status_text
        assert pilot.app.query_one("#technical").has_class("failed")


async def test_app_registers_and_applies_custom_theme():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.theme == "productagents"


async def test_app_panel_titles_show_state_icons():
    from productagents.agents.runner import FinishedEvent, NodeCompleteEvent
    from productagents.core.models import AnalystReport, Evidence, Recommendation

    async def fake_runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        yield NodeCompleteEvent(
            node="market",
            report=AnalystReport(
                analyst="market", role="Market Analyst", findings=["x"], signals=[]
            ),
        )
        yield FinishedEvent(
            recommendation=Recommendation(
                recommendation="Build it",
                confidence=0.5,
                rationale="r",
                expected_outcomes=["o"],
            ),
            reports=[],
            debate=[],
            risks=[],
            governance=None,
        )

    evidence = Evidence(
        scenario="sample", customer_feedback="d", product_analytics={"x": 1}
    )
    app = ProductAgentsApp(
        fake_runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        # Idle on mount.
        assert str(app.query_one("#technical").border_title).startswith("·")
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        # Completed analyst shows the done icon.
        assert "✓" in str(app.query_one("#market").border_title)


async def test_reset_panels_marks_downstream_waiting():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app._reset_panels()
        # Downstream panels wait on upstream output.
        for widget_id in (
            "debate-scroll",
            "strategist",
            "judgment",
            "risk-scroll",
            "governance",
        ):
            assert str(app.query_one(f"#{widget_id}").border_title).startswith("◌")
        # Analysts and recall do not wait — they start immediately.
        assert str(app.query_one("#technical").border_title).startswith("·")
        assert str(app.query_one("#recall").border_title).startswith("·")


async def test_app_uses_three_lane_layout_with_analyst_grid():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        # New lane containers exist.
        app.query_one("#left-lane")
        app.query_one("#center-lane")
        app.query_one("#right-lane")
        grid = app.query_one("#analyst-grid")
        # All five analyst panels live inside the grid.
        for analyst_id in (
            "customer_research",
            "product_analytics",
            "market",
            "business",
            "technical",
        ):
            assert app.query_one(f"#{analyst_id}") in grid.query(".analyst")
        # Existing panels are still reachable by id.
        app.query_one("#debate")
        app.query_one("#risk")
        app.query_one("#governance")
        app.query_one("#strategist")
        app.query_one("#judgment")
        app.query_one("#recall")
        app.query_one("#evidence-provenance")
        app.query_one("#status-log")
        app.query_one("#pipeline-rail")


async def test_app_renders_and_records_judgment(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, evidence = _runner_and_evidence()
    recorded = []
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        judge_text = str(pilot.app.query_one("#judgment").content)

    assert "PASS" in judge_text
    assert len(recorded) == 1
    assert recorded[0].judgment is not None
    assert recorded[0].judgment.passed is True


async def test_running_state_shows_advancing_spinner_that_stops_on_done():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app._set_state("market", "running")
        title_before = str(app.query_one("#market").border_title)
        assert title_before[0] in "◐◓◑◒"
        assert "market" in app._spinning
        # Advancing the timer rotates the frame.
        app._advance_spinner()
        title_after = str(app.query_one("#market").border_title)
        assert title_after[0] in "◐◓◑◒"
        assert title_after != title_before
        # Reaching a terminal state stops the spin and paints the static icon.
        app._set_state("market", "done")
        assert "market" not in app._spinning
        assert str(app.query_one("#market").border_title).startswith("✓")


async def test_judgment_failure_shows_warning():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app._on_judgment(
            JudgmentEvent(
                evidence_grounding_score=0.4,
                rationale_coherence_score=0.5,
                passed=False,
                critique="weak grounding",
                attempt=1,
            )
        )
        panel = app.query_one("#judgment")
        assert str(panel.border_title).startswith("⚠")
        assert panel.has_class("warning")


async def test_governance_non_approve_warns_then_approval_clears_it():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app._on_governance_verdict(
            GovernanceVerdictEvent(verdict="reject", rationale="not now")
        )
        gov = app.query_one("#governance")
        assert str(gov.border_title).startswith("⚠")
        assert gov.has_class("warning")
        # A human override to approve clears the warning.
        app._on_final_verdict(
            FinalVerdictEvent(verdict="approve", rationale="ok", decided_by="human")
        )
        assert str(gov.border_title).startswith("✓")
        assert not gov.has_class("warning")


async def test_debate_panel_runs_then_done_when_strategist_starts():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app._on_debate_turn(
            DebateTurnEvent(round=1, side="advocate", argument="ship it")
        )
        assert "debate-scroll" in app._spinning  # running spinner
        app._on_progress(ProgressEvent(node="strategist", message="thinking"))
        assert str(app.query_one("#debate-scroll").border_title).startswith("✓")
        assert "strategist" in app._spinning


async def test_strategist_done_when_judgment_arrives():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app._on_progress(ProgressEvent(node="strategist", message="thinking"))
        assert "strategist" in app._spinning
        app._on_judgment(
            JudgmentEvent(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                passed=True,
                critique="ok",
                attempt=1,
            )
        )
        assert str(app.query_one("#strategist").border_title).startswith("✓")
        assert "strategist" not in app._spinning


async def test_risk_panel_runs_then_done_when_governance_arrives():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        app._on_risk_assessment(
            RiskAssessmentEvent(
                reviewer="r", role="Risk Reviewer", level="medium", rationale="some"
            )
        )
        assert "risk-scroll" in app._spinning
        app._on_governance_verdict(
            GovernanceVerdictEvent(verdict="approve", rationale="go")
        )
        assert str(app.query_one("#risk-scroll").border_title).startswith("✓")
        assert "risk-scroll" not in app._spinning


# ---------------------------------------------------------------------------
# Degraded-run helpers
# ---------------------------------------------------------------------------


def _degraded_evidence():
    return Evidence(
        scenario="sample", customer_feedback="x", product_analytics={"a": 1}
    )


def _failed_finished():
    rec = Recommendation(
        recommendation="Unable to produce a recommendation due to an error.",
        confidence=0.0,
        rationale="Strategist failed: boom",
        expected_outcomes=[],
        failed=True,
    )
    return FinishedEvent(
        recommendation=rec, reports=[], debate=[], risks=[], governance=None
    )


def _ok_finished():
    rec = Recommendation(
        recommendation="Build SSO",
        confidence=0.8,
        rationale="demand",
        expected_outcomes=["growth"],
    )
    return FinishedEvent(
        recommendation=rec, reports=[], debate=[], risks=[], governance=None
    )


def _runner_yielding(*events):
    async def _runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        for e in events:
            yield e

    return _runner


async def test_failed_run_is_not_auto_recorded_and_shows_modal(monkeypatch):
    recorded = []
    chosen = {}

    app = ProductAgentsApp(
        _runner_yielding(_failed_finished()),
        _degraded_evidence(),
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async def fake_push_screen_wait(screen):
        chosen["screen"] = type(screen).__name__
        return "quit"

    async with app.run_test() as pilot:
        monkeypatch.setattr(app, "push_screen_wait", fake_push_screen_wait)
        app._run(Initiative(title="SSO", description="SSO"), _degraded_evidence())
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()

    assert chosen["screen"] == "DegradedRunScreen"
    assert recorded == []  # quit records nothing


async def test_decide_path_records_human_decision(monkeypatch):
    recorded = []

    app = ProductAgentsApp(
        _runner_yielding(_failed_finished()),
        _degraded_evidence(),
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async def fake_push_screen_wait(screen):
        if isinstance(screen, DegradedRunScreen):
            return "decide"
        return HumanDecision(verdict="reject", rationale="not now")

    async with app.run_test() as pilot:
        monkeypatch.setattr(app, "push_screen_wait", fake_push_screen_wait)
        app._run(Initiative(title="SSO", description="SSO"), _degraded_evidence())
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()

    assert len(recorded) == 1
    record = recorded[0]
    assert record.governance.verdict == "reject"
    assert record.governance.decided_by == "human"


async def test_healthy_run_is_recorded(monkeypatch):
    recorded = []

    app = ProductAgentsApp(
        _runner_yielding(_ok_finished()),
        _degraded_evidence(),
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async with app.run_test() as pilot:
        app._run(Initiative(title="SSO", description="SSO"), _degraded_evidence())
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO"


async def test_retry_path_reruns(monkeypatch):
    """Choosing 'retry' from DegradedRunScreen re-runs and records the healthy result."""  # noqa: E501
    recorded = []

    # A stateful runner: first call yields a failed event, second yields a healthy one.
    calls: list[list] = [
        [_failed_finished()],
        [_ok_finished()],
    ]

    async def stateful_runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        events = calls.pop(0)
        for e in events:
            yield e

    app = ProductAgentsApp(
        stateful_runner,
        _degraded_evidence(),
        recorder=recorded.append,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )

    async def fake_push_screen_wait(screen):
        if isinstance(screen, DegradedRunScreen):
            return "retry"
        return None  # should not be reached in this path

    async with app.run_test() as pilot:
        monkeypatch.setattr(app, "push_screen_wait", fake_push_screen_wait)
        app._run(Initiative(title="SSO", description="SSO"), _degraded_evidence())
        await pilot.pause()
        # Wait for the first worker (failed run + modal handling) to finish.
        await app.workers.wait_for_complete()
        await pilot.pause()
        # The retry spawns a second @work(exclusive=True) worker; wait for it too.
        await app.workers.wait_for_complete()
        await pilot.pause()

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO"


async def test_right_lane_panels_stay_on_screen_with_long_content():
    """Regression: long strategist/judge/risk/governance content must not push
    the lower right-lane panels off-screen. They share the lane height (1fr)
    and scroll internally instead of growing unbounded."""
    long_text = ("rationale text that is quite long and wraps many times " * 8).strip()
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"]),
            DebateArgument: DebateArgument(argument=long_text),
            Recommendation: Recommendation(
                recommendation="Build SSO now",
                confidence=0.81,
                rationale=long_text,
                expected_outcomes=[
                    "enterprise unblock",
                    "reduced churn",
                    "bigger deals",
                ],
            ),
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique=long_text,
            ),
            RiskFinding: RiskFinding(level="medium", rationale=long_text),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale=long_text
            ),
        }
    )
    graph = build_graph(model)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    app = ProductAgentsApp(
        partial(run_decision, graph),
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test(size=(120, 40)) as pilot:
        pilot.app.query_one("#initiative-title").value = "Add enterprise SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        screen_h = pilot.app.screen.region.height
        for widget_id in ("strategist", "judgment", "risk-scroll", "governance"):
            region = pilot.app.query_one(f"#{widget_id}").region
            assert region.height > 0, f"{widget_id} collapsed to zero height"
            assert region.y >= 0, f"{widget_id} pushed above the screen"
            assert region.y + region.height <= screen_h, (
                f"{widget_id} pushed off-screen"
            )


async def test_strategist_panel_renders_on_recommendation_event():
    from productagents.agents.runner import RecommendationEvent
    from productagents.core.models import Initiative, Recommendation

    async def fake_runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        yield RecommendationEvent(
            recommendation=Recommendation(
                recommendation="Build SSO now",
                confidence=0.82,
                rationale="Enterprise demand is clear.",
                expected_outcomes=["Higher enterprise conversion"],
            )
        )

    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    app = ProductAgentsApp(
        fake_runner,
        evidence,
        recorder=lambda record: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        app._run(Initiative(title="Add SSO", description="Add SSO"), evidence)
        await pilot.pause()
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        strat_text = str(pilot.app.query_one("#strategist").content)
        strat_title = str(pilot.app.query_one("#strategist").border_title)

    assert "Build SSO now" in strat_text
    assert "82%" in strat_text
    assert strat_title.startswith("✓")


async def test_pipeline_rail_advances_during_a_run():
    from productagents.app.tui.rail import PipelineRail

    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title", Input).value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        rail_text = str(pilot.app.query_one("#pipeline-rail", PipelineRail).content)
        # After a full healthy run the rail shows completed stages and a 5/5 count.
        assert "✓" in rail_text
        assert "5/5" in rail_text


async def test_status_log_turns_red_only_on_error():
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        status = app.query_one("#status-log")
        assert not status.has_class("-has-error")
        app._log_status("just info", level="info")
        assert not status.has_class("-has-error")
        app._log_status("boom", level="error")
        assert status.has_class("-has-error")
        app._reset_panels()
        assert not status.has_class("-has-error")
