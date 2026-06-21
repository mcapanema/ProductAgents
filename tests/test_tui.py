from functools import partial

import pytest

from productagents.graph import build_graph
from productagents.runner import run_decision
from productagents.schemas import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    Recommendation,
    RiskFinding,
)
from productagents.tui.app import ProductAgentsApp
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


def test_main_reports_clear_error_when_model_init_fails(monkeypatch, capsys):
    import productagents.tui.app as app_module

    def boom():
        raise RuntimeError("no api key")

    monkeypatch.setattr(app_module, "get_model", boom)
    with pytest.raises(SystemExit) as excinfo:
        app_module.main()
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "PRODUCTAGENTS_MODEL" in err
    assert "api key" in err.lower()


async def test_app_renders_new_analyst_panels(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, evidence = _runner_and_evidence()
    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
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
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#evidence-source").value = "/no/such/source/xyz"
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.pause()
        strat_text = str(pilot.app.query_one("#strategist").content)

    assert ran["called"] is False
    assert "Evidence" in strat_text or "evidence" in strat_text


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
