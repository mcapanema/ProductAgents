from functools import partial

from textual.widgets import Button

from productagents.graph import build_graph
from productagents.runner import run_decision
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    JudgeFinding,
    Recommendation,
    RiskFinding,
)
from productagents.setup import ConfigStatus
from productagents.tui.app import ProductAgentsApp
from productagents.tui.home_screen import HomeScreen
from productagents.tui.setup_screen import SetupScreen
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


async def test_app_renders_recalled_lessons(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    from productagents.schemas import (
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

    from productagents.evidence import collect_evidence

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

    from productagents.evidence import collect_evidence

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

    from productagents.evidence import collect_evidence

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
    from productagents.runner import FinishedEvent, NodeCompleteEvent
    from productagents.schemas import AnalystReport, Evidence, Recommendation

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
    from productagents.runner import FinishedEvent, NodeErrorEvent
    from productagents.schemas import Evidence, Recommendation

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
    from productagents.runner import FinishedEvent, NodeCompleteEvent
    from productagents.schemas import AnalystReport, Evidence, Recommendation

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
        app.query_one("#recall")
        app.query_one("#evidence-provenance")
        app.query_one("#status-log")
