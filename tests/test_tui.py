import pytest
from functools import partial

from productagents.graph import build_graph
from productagents.runner import run_decision
from productagents.schemas import AnalystFindings, Evidence, Recommendation
from productagents.tui.app import ProductAgentsApp
from tests.fakes import FakeChatModel


def _runner_and_evidence():
    model = FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"]),
            Recommendation: Recommendation(
                recommendation="Build SSO now",
                confidence=0.81,
                rationale="strong demand",
                expected_outcomes=["enterprise unblock"],
            ),
        }
    )
    graph = build_graph(model)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    return partial(run_decision, graph), evidence


async def test_app_renders_recommendation_and_records(tmp_path):
    runner, evidence = _runner_and_evidence()
    recorded = []

    def recorder(record):
        recorded.append(record)

    app = ProductAgentsApp(runner, evidence, recorder=recorder)

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        # In Textual 8.x, Static has .content (not .renderable); use str() for both
        strategist = pilot.app.query_one("#strategist")
        result_text = str(strategist.content)
        assert "Build SSO now" in result_text

    assert len(recorded) == 1
    assert recorded[0].recommendation.recommendation == "Build SSO now"
    assert recorded[0].initiative.title == "Add SSO"


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
