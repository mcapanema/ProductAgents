from productagents.agents.strategist import _prompt as strategist_prompt
from productagents.agents.strategist import strategist_node
from productagents.core.models import AnalystReport, Initiative, Recommendation
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "reports": [
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["strong enterprise demand"],
                signals=["18 tickets"],
            ),
            AnalystReport(
                analyst="product_analytics",
                role="Product Analytics Analyst",
                findings=["30% onboarding drop-off"],
                signals=["funnel data"],
            ),
        ],
    }


def test_strategist_prompt_renders_lessons_and_critique_from_store():
    from productagents.agents.prompts import PromptStore

    out = strategist_prompt(
        Initiative(title="t", description="d"),
        reports=[],
        debate=[],
        prior_lessons=["LESSON-X"],
        judgment=None,
        prompts=PromptStore(),
    )
    assert "Product Strategist" in out
    assert "LESSON-X" in out


async def test_strategist_returns_recommendation():
    expected = Recommendation(
        recommendation="Build SSO this quarter",
        confidence=0.82,
        rationale="Demand plus measurable onboarding friction.",
        expected_outcomes=["unblock enterprise deals"],
    )
    model = FakeChatModel({Recommendation: expected})
    result = await strategist_node(_state(), model)
    assert result["recommendation"] == expected


async def test_strategist_failure_yields_zero_confidence():
    model = FakeChatModel({Recommendation: RuntimeError("LLM down")})
    result = await strategist_node(_state(), model)
    rec = result["recommendation"]
    assert rec.confidence == 0.0
    assert "unable" in rec.recommendation.lower()
    assert rec.failed is True


async def test_strategist_includes_debate_in_prompt(monkeypatch):
    from productagents.agents import strategist as strategist_module
    from productagents.core.models import DebateTurn

    captured = {}

    def fake_format_transcript(turns, *, empty="(no debate)"):
        captured["turns"] = turns
        return "DEBATE-BLOCK"

    monkeypatch.setattr(strategist_module, "format_transcript", fake_format_transcript)

    state = _state()
    state["debate"] = [DebateTurn(round=1, side="advocate", argument="for it")]

    from productagents.core.models import Recommendation

    model = FakeChatModel(
        {
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            )
        }
    )
    result = await strategist_node(state, model)
    assert result["recommendation"].recommendation == "Build it"
    assert captured["turns"][0].side == "advocate"


async def test_strategist_includes_prior_lessons_in_prompt(monkeypatch):
    from productagents.agents import strategist as strategist_module

    captured = {}

    def fake_format_lessons(lessons):
        captured["lessons"] = lessons
        return "LESSONS-BLOCK"

    monkeypatch.setattr(strategist_module, "_format_lessons", fake_format_lessons)

    state = _state()
    state["prior_lessons"] = ['From "Add SSO login": SSO took two quarters']

    model = FakeChatModel(
        {
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            )
        }
    )
    result = await strategist_node(state, model)
    assert result["recommendation"].recommendation == "Build it"
    assert captured["lessons"] == ['From "Add SSO login": SSO took two quarters']


async def test_format_critique_empty_when_no_judgment():
    from productagents.agents.strategist import _format_critique

    assert _format_critique(None) == ""


async def test_strategist_degrades_when_model_returns_none():
    model = FakeChatModel({Recommendation: None})
    state = {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "reports": [],
        "debate": [],
        "prior_lessons": [],
        "judgment": None,
    }
    result = await strategist_node(state, model)
    rec = result["recommendation"]
    assert rec.failed is True
    assert rec.confidence == 0.0


async def test_strategist_injects_judge_critique_on_retry(monkeypatch):
    from productagents.agents import strategist as strategist_module
    from productagents.core.models import JudgeVerdict

    captured = {}

    def fake_format_critique(judgment):
        captured["judgment"] = judgment
        return "CRITIQUE-BLOCK"

    monkeypatch.setattr(strategist_module, "_format_critique", fake_format_critique)

    state = _state()
    state["judgment"] = JudgeVerdict(
        evidence_grounding_score=0.2,
        rationale_coherence_score=0.3,
        passed=False,
        critique="cite the funnel data",
        attempt=1,
    )

    model = FakeChatModel(
        {
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            )
        }
    )
    result = await strategist_node(state, model)
    assert result["recommendation"].recommendation == "Build it"
    assert captured["judgment"].critique == "cite the funnel data"
