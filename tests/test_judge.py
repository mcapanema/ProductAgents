from productagents.agents.judge import (
    DEFAULT_JUDGE_MAX_RETRIES,
    DEFAULT_JUDGE_THRESHOLD,
    get_judge_max_retries,
    get_judge_threshold,
    judge_node,
)
from productagents.schemas import (
    AnalystReport,
    Initiative,
    JudgeFinding,
    Recommendation,
)
from tests.fakes import FakeChatModel


def _state(judge_attempts: int = 0):
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "recommendation": Recommendation(
            recommendation="Build SSO this quarter",
            confidence=0.8,
            rationale="Demand plus onboarding friction.",
            expected_outcomes=["unblock enterprise deals"],
        ),
        "reports": [
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["strong enterprise demand"],
                signals=["18 tickets"],
            ),
        ],
        "debate": [],
        "judge_attempts": judge_attempts,
    }


async def test_judge_passes_when_both_scores_meet_threshold():
    model = FakeChatModel(
        {
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.85,
                critique="well grounded",
            )
        }
    )
    result = await judge_node(_state(), model)
    verdict = result["judgment"]
    assert verdict.passed is True
    assert verdict.attempt == 1
    assert result["judge_attempts"] == 1


async def test_judge_fails_when_a_score_is_below_threshold():
    model = FakeChatModel(
        {
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.4,
                critique="rationale does not follow",
            )
        }
    )
    result = await judge_node(_state(), model)
    assert result["judgment"].passed is False


async def test_judge_increments_attempt_from_state():
    model = FakeChatModel(
        {
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.2,
                rationale_coherence_score=0.2,
                critique="weak",
            )
        }
    )
    result = await judge_node(_state(judge_attempts=1), model)
    assert result["judgment"].attempt == 2
    assert result["judge_attempts"] == 2


async def test_judge_respects_custom_threshold(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_THRESHOLD", "0.95")
    model = FakeChatModel(
        {
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="good but not great",
            )
        }
    )
    result = await judge_node(_state(), model)
    assert result["judgment"].passed is False


async def test_judge_degrades_to_passing_on_failure():
    model = FakeChatModel({JudgeFinding: RuntimeError("judge LLM down")})
    result = await judge_node(_state(), model)
    verdict = result["judgment"]
    assert verdict.failed is True
    assert verdict.passed is True  # a broken judge never blocks the pipeline
    assert "unavailable" in verdict.critique


def test_get_judge_threshold_parsing(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_JUDGE_THRESHOLD", raising=False)
    assert get_judge_threshold() == DEFAULT_JUDGE_THRESHOLD
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_THRESHOLD", "0.85")
    assert get_judge_threshold() == 0.85
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_THRESHOLD", "garbage")
    assert get_judge_threshold() == DEFAULT_JUDGE_THRESHOLD
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_THRESHOLD", "1.5")  # out of range
    assert get_judge_threshold() == DEFAULT_JUDGE_THRESHOLD


async def test_judge_degrades_when_model_returns_none():
    model = FakeChatModel({JudgeFinding: None})
    state = {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "recommendation": Recommendation(
            recommendation="ship", confidence=0.5, rationale="r", expected_outcomes=[]
        ),
        "reports": [],
        "debate": [],
        "judge_attempts": 0,
    }
    result = await judge_node(state, model)
    verdict = result["judgment"]
    assert verdict.failed is True
    assert verdict.passed is True  # a broken judge never blocks


def test_get_judge_max_retries_parsing(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", raising=False)
    assert get_judge_max_retries() == DEFAULT_JUDGE_MAX_RETRIES
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "3")
    assert get_judge_max_retries() == 3
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "0")  # score-only is valid
    assert get_judge_max_retries() == 0
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "-2")  # negative -> default
    assert get_judge_max_retries() == DEFAULT_JUDGE_MAX_RETRIES
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "garbage")
    assert get_judge_max_retries() == DEFAULT_JUDGE_MAX_RETRIES
