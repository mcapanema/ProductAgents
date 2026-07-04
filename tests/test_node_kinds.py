"""The node-kind registry — palette + I/O contracts + builders."""

from langgraph.graph import END

from productagents.agents.context import AgentContext
from productagents.agents.node_kinds import (
    KIND_REGISTRY,
    PLACEABLE,
    NodeKind,
    route_after_judge,
    route_after_strategist,
)
from productagents.core.models import JudgeVerdict, Recommendation
from tests.fakes import FakeChatModel


def _recommendation(*, failed: bool) -> Recommendation:
    return Recommendation(
        recommendation="ship it",
        confidence=0.8,
        rationale="because",
        expected_outcomes=["outcome"],
        failed=failed,
    )


def _verdict(*, passed: bool) -> JudgeVerdict:
    return JudgeVerdict(
        evidence_grounding_score=0.8,
        rationale_coherence_score=0.8,
        passed=passed,
        critique="fine",
        attempt=1,
    )


def test_registry_covers_the_current_pipeline_kinds():
    assert set(KIND_REGISTRY) == {
        "customer_research",
        "product_analytics",
        "market",
        "business",
        "technical",
        "recall",
        "debate",
        "strategist",
        "judge",
        "risk",
        "governance",
    }
    assert set(PLACEABLE) == set(KIND_REGISTRY)


def test_analysts_are_duplicable_others_are_singletons():
    assert KIND_REGISTRY["market"].singleton is False
    for k in ["recall", "debate", "strategist", "judge", "risk", "governance"]:
        assert KIND_REGISTRY[k].singleton is True


def test_io_contracts_match_graphstate_keys():
    r = KIND_REGISTRY
    assert r["market"].reads == frozenset({"initiative", "evidence"})
    assert r["market"].writes == frozenset({"reports"})
    assert r["recall"].reads == frozenset({"initiative"})
    assert r["recall"].writes == frozenset({"prior_lessons"})
    assert r["debate"].reads == frozenset({"reports"})
    assert r["debate"].writes == frozenset({"debate"})
    assert r["strategist"].reads == frozenset({"debate", "prior_lessons"})
    assert r["strategist"].writes == frozenset({"recommendation"})
    assert r["judge"].reads == frozenset({"recommendation"})
    assert r["judge"].writes == frozenset({"judgment", "judge_attempts"})
    assert r["risk"].reads == frozenset({"recommendation"})
    assert r["risk"].writes == frozenset({"risks"})
    assert r["governance"].reads == frozenset({"recommendation", "risks"})
    assert r["governance"].writes == frozenset({"governance"})


def test_conditional_kinds_carry_routers():
    assert callable(KIND_REGISTRY["strategist"].router)
    assert KIND_REGISTRY["strategist"].router_targets is not None
    assert callable(KIND_REGISTRY["judge"].router)
    assert KIND_REGISTRY["judge"].router_targets is not None
    assert KIND_REGISTRY["market"].router is None


def test_build_returns_a_callable_node():
    ctx = AgentContext(model=FakeChatModel({}))
    node = KIND_REGISTRY["market"].build(ctx, {})
    assert callable(node)
    assert isinstance(KIND_REGISTRY["debate"], NodeKind)


def test_route_after_strategist_ends_when_no_recommendation():
    assert route_after_strategist({"recommendation": None}) == END


def test_route_after_strategist_ends_when_recommendation_failed():
    state = {"recommendation": _recommendation(failed=True)}
    assert route_after_strategist(state) == END


def test_route_after_strategist_advances_to_judge_on_success():
    state = {"recommendation": _recommendation(failed=False)}
    assert route_after_strategist(state) == "judge"


def test_route_after_judge_advances_to_risk_when_no_judgment():
    assert route_after_judge({"judgment": None, "judge_attempts": 0}) == "risk"


def test_route_after_judge_advances_to_risk_on_pass():
    state = {"judgment": _verdict(passed=True), "judge_attempts": 0}
    assert route_after_judge(state) == "risk"


def test_route_after_judge_retries_strategist_on_fail_within_budget(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "1")
    state = {"judgment": _verdict(passed=False), "judge_attempts": 1}
    assert route_after_judge(state) == "strategist"


def test_route_after_judge_advances_to_risk_when_retries_exhausted(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_JUDGE_MAX_RETRIES", "1")
    state = {"judgment": _verdict(passed=False), "judge_attempts": 2}
    assert route_after_judge(state) == "risk"
