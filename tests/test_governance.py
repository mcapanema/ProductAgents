import logging

from productagents.agents.context import AgentContext
from productagents.agents.governance import _format_portfolio, governance_node
from productagents.agents.governance import _prompt as governance_prompt
from productagents.core.enums import Verdict
from productagents.core.models import (
    DecisionRecord,
    GovernanceFinding,
    GovernanceVerdict,
    Initiative,
    Recommendation,
    RiskAssessment,
)
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "recommendation": Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="strong demand",
            expected_outcomes=["growth"],
        ),
        "risks": [
            RiskAssessment(
                reviewer="delivery",
                role="Delivery Risk Reviewer",
                level="medium",
                rationale="some integration work",
            )
        ],
    }


def _prior_record(title: str, verdict: Verdict) -> DecisionRecord:
    return DecisionRecord(
        initiative=Initiative(title=title, description="d"),
        recommendation=Recommendation(
            recommendation="ship", confidence=0.5, rationale="x", expected_outcomes=[]
        ),
        reports=[],
        governance=GovernanceVerdict(verdict=verdict, rationale="prior"),
        timestamp="2026-06-19T12:00:00+00:00",
    )


class _FakeLearning:
    """Minimal LessonReader for governance tests."""

    def __init__(self, decisions=None, raise_on_decisions=False):
        self._decisions = decisions or []
        self._raise = raise_on_decisions

    async def relevant_lessons(self, initiative):
        return []

    async def decisions(self):
        if self._raise:
            raise RuntimeError("store unavailable")
        return self._decisions


def _ctx(model, decisions=None, raise_on_decisions=False):
    return AgentContext(
        model=model,
        learning=_FakeLearning(
            decisions=decisions, raise_on_decisions=raise_on_decisions
        ),
    )


def test_governance_prompt_renders_from_store():
    from productagents.agents.prompts import PromptStore

    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    recommendation = Recommendation(
        recommendation="Build it",
        confidence=0.7,
        rationale="demand",
        expected_outcomes=[],
    )
    out = governance_prompt(initiative, recommendation, [], [], PromptStore())
    assert "Portfolio Manager" in out
    assert "Add SSO" in out


def test_format_portfolio_handles_empty():
    assert _format_portfolio([]) == "(no prior decisions)"


def test_format_portfolio_summarizes_prior_decisions():
    summary = _format_portfolio([_prior_record("Old Feature", "approve")])
    assert "Old Feature" in summary
    assert "approve" in summary


async def test_governance_node_produces_verdict():
    model = FakeChatModel(
        {GovernanceFinding: GovernanceFinding(verdict="approve", rationale="worth it")}
    )
    result = await governance_node(_state(), model, _ctx(model))
    verdict = result["governance"]
    assert verdict.verdict == "approve"
    assert verdict.rationale == "worth it"
    assert verdict.failed is False


async def test_governance_node_degrades_on_failure():
    model = FakeChatModel({GovernanceFinding: RuntimeError("LLM down")})
    result = await governance_node(_state(), model, _ctx(model))
    verdict = result["governance"]
    assert verdict.failed is True
    assert verdict.verdict == "error"
    assert "unavailable" in verdict.rationale


async def test_governance_degrades_when_model_returns_none():
    model = FakeChatModel({GovernanceFinding: None})
    state = {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "recommendation": Recommendation(
            recommendation="ship", confidence=0.5, rationale="r", expected_outcomes=[]
        ),
        "risks": [],
    }
    result = await governance_node(state, model, _ctx(model))
    verdict = result["governance"]
    assert verdict.failed is True
    assert verdict.verdict == "error"


async def test_governance_receives_portfolio_from_learning_service(monkeypatch):
    """The node passes the portfolio it fetched from ctx.learning into _prompt."""
    import productagents.agents.governance as gov

    prior = _prior_record("Old Feature", "approve")
    model = FakeChatModel(
        {GovernanceFinding: GovernanceFinding(verdict="approve", rationale="ok")}
    )
    ctx = _ctx(model, decisions=[prior])

    captured = {}
    real_prompt = gov._prompt

    def _capture(initiative, recommendation, risks, portfolio, prompts):
        captured["portfolio"] = portfolio
        return real_prompt(initiative, recommendation, risks, portfolio, prompts)

    monkeypatch.setattr(gov, "_prompt", _capture)
    result = await governance_node(_state(), model, ctx)

    assert result["governance"].verdict == "approve"
    # End-to-end: the fetched portfolio reached _prompt (not [] or discarded).
    assert captured["portfolio"] == [prior]
    assert "Old Feature" in _format_portfolio(captured["portfolio"])


async def test_governance_degrades_portfolio_when_learning_raises():
    """A storage failure on decisions() is swallowed; node still produces a verdict."""
    model = FakeChatModel(
        {GovernanceFinding: GovernanceFinding(verdict="reject", rationale="too risky")}
    )
    ctx = _ctx(model, raise_on_decisions=True)
    result = await governance_node(_state(), model, ctx)
    # Node must not crash and portfolio falls back to empty (no prior decisions).
    assert result["governance"].failed is False
    assert result["governance"].verdict == "reject"


async def test_governance_logs_and_emits_when_portfolio_fetch_fails(
    monkeypatch, caplog
):
    import productagents.agents.governance as gov_mod
    from productagents.agents.stream_events import NODE, STATUS

    emitted: list[dict] = []
    monkeypatch.setattr(gov_mod, "get_writer", lambda: emitted.append)

    model = FakeChatModel(
        {GovernanceFinding: GovernanceFinding(verdict="reject", rationale="too risky")}
    )
    ctx = _ctx(model, raise_on_decisions=True)

    with caplog.at_level(logging.WARNING):
        result = await governance_node(_state(), model, ctx)

    # Node still produces a verdict (portfolio fetch failing is a soft degrade).
    assert result["governance"].failed is False
    assert result["governance"].verdict == "reject"
    # It is now observable: logged with a trace + a status line for the UI.
    assert "portfolio" in caplog.text.lower()
    assert any(
        chunk.get(NODE) == "governance"
        and "portfolio unavailable" in str(chunk.get(STATUS, ""))
        for chunk in emitted
    )


async def test_null_learning_yields_no_prior_decisions():
    """_NullLearning (default AgentContext) returns [] for decisions()."""
    model = FakeChatModel(
        {GovernanceFinding: GovernanceFinding(verdict="approve", rationale="fine")}
    )
    ctx = AgentContext(model=model)  # _NullLearning default
    result = await governance_node(_state(), model, ctx)
    assert result["governance"].verdict == "approve"
