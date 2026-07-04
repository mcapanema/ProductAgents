"""The node-kind registry — palette + I/O contracts + builders."""

from productagents.agents.context import AgentContext
from productagents.agents.node_kinds import KIND_REGISTRY, PLACEABLE, NodeKind
from tests.fakes import FakeChatModel


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
