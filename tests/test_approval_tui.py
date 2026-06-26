from functools import partial

from textual.widgets import Input, Static

from productagents.agents.graph import build_graph
from productagents.agents.runner import run_decision
from productagents.app.tui.app import ProductAgentsApp
from productagents.app.tui.approval import ApprovalScreen
from productagents.core.models import (
    AnalystFindings,
    DebateArgument,
    Evidence,
    GovernanceFinding,
    JudgeFinding,
    Recommendation,
    RiskFinding,
)
from tests.fakes import FakeChatModel


def _hitl_runner_and_evidence():
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
    graph = build_graph(model, human_in_the_loop=True)
    evidence = Evidence(
        scenario="sample", customer_feedback="demand", product_analytics={"x": 1}
    )
    return partial(run_decision, graph), evidence


async def _empty_reader():
    return []


def _list_recorder(lst):
    async def _record(r):
        lst.append(r)

    return _record


async def test_human_reject_overrides_advisory_and_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    runner, evidence = _hitl_runner_and_evidence()
    recorded = []

    app = ProductAgentsApp(
        runner,
        evidence,
        recorder=_list_recorder(recorded),
        reader=_empty_reader,
        show_home=False,
    )

    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title", Input).value = "Add SSO"
        await pilot.press("enter")
        # Let the graph run to the governance interrupt, which pushes the modal.
        for _ in range(50):
            await pilot.pause()
            if isinstance(pilot.app.screen, ApprovalScreen):
                break
        assert isinstance(pilot.app.screen, ApprovalScreen)

        pilot.app.screen.query_one("#note").value = "No capacity this quarter."
        await pilot.click("#reject")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()

        gov_text = str(pilot.app.query_one("#governance", Static).content)
        assert "reject" in gov_text
        assert "human" in gov_text

    assert len(recorded) == 1
    verdict = recorded[0].governance
    assert verdict.verdict == "reject"
    assert verdict.decided_by == "human"
    assert verdict.advisory_verdict == "approve"
