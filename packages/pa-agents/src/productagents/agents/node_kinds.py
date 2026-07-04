"""Node-kind registry: the palette of placeable node kinds + their contracts.

Each kind wraps an EXISTING graph node (same builder wiring ``graph.py`` uses) and
declares which ``GraphState`` keys it reads/writes. The validator uses those I/O
contracts to guarantee every saved definition compiles & runs; the dynamic builder
uses ``build`` to construct nodes. The two conditional routers live here because a
kind owns its own routing (strategist fail-fast, judge retry loop).

ponytail: each existing node is its own kind (keyed by its current node name), so
``topology.py`` / the GUI keep working unchanged and 'duplicate an analyst' is just
a second instance of the ``market`` kind. ``human_approval`` is deliberately NOT a
placeable kind — HITL stays a builder-managed run-flag (see graph.py).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from langgraph.graph import END

from productagents.agents.business import business_node
from productagents.agents.context import AgentContext
from productagents.agents.customer_research import customer_research_node
from productagents.agents.debate import debate_node
from productagents.agents.governance import governance_node
from productagents.agents.judge import get_judge_max_retries, judge_node
from productagents.agents.market import market_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.recall import recall_node
from productagents.agents.risk import risk_node
from productagents.agents.strategist import strategist_node
from productagents.agents.technical import technical_node


def route_after_strategist(state) -> str:
    """Fail fast: end the run when the strategist could not produce a rec."""
    recommendation = state.get("recommendation")
    if recommendation is None or recommendation.failed:
        return END
    return "judge"


def route_after_judge(state) -> str:
    """Route forward to risk on pass/exhausted retries, else back to strategist."""
    judgment = state.get("judgment")
    if judgment is None or judgment.passed:
        return "risk"
    if state.get("judge_attempts", 0) > get_judge_max_retries():
        return "risk"
    return "strategist"


@dataclass(frozen=True)
class NodeKind:
    kind: str
    label: str
    role: str  # matches the GUI's KIND_META roles (analyst/debate/decision/...)
    singleton: bool
    reads: frozenset[str]
    writes: frozenset[str]
    prompts: tuple[str, ...]
    build: Callable[[AgentContext, dict], Callable]
    router: Callable | None = None
    # sentinel(node-id or END) -> target(node-id or END); passed to
    # add_conditional_edges
    router_targets: dict | None = None


def _analyst_build(node_fn):
    return lambda ctx, config: partial(node_fn, ctx=ctx)


def _llm_build(node_fn):
    return lambda ctx, config: partial(node_fn, model=ctx.model, prompts=ctx.prompts)


def _analyst(kind: str, label: str) -> NodeKind:
    node_fn = {
        "customer_research": customer_research_node,
        "product_analytics": product_analytics_node,
        "market": market_node,
        "business": business_node,
        "technical": technical_node,
    }[kind]
    return NodeKind(
        kind=kind,
        label=label,
        role="analyst",
        singleton=False,
        reads=frozenset({"initiative", "evidence"}),
        writes=frozenset({"reports"}),
        prompts=(kind,),
        build=_analyst_build(node_fn),
    )


KIND_REGISTRY: dict[str, NodeKind] = {
    "customer_research": _analyst("customer_research", "Customer Research"),
    "product_analytics": _analyst("product_analytics", "Product Analytics"),
    "market": _analyst("market", "Market"),
    "business": _analyst("business", "Business"),
    "technical": _analyst("technical", "Technical"),
    "recall": NodeKind(
        kind="recall",
        label="Recall",
        role="memory",
        singleton=True,
        reads=frozenset({"initiative"}),
        writes=frozenset({"prior_lessons"}),
        prompts=(),
        build=lambda ctx, config: partial(recall_node, ctx=ctx),
    ),
    "debate": NodeKind(
        kind="debate",
        label="Debate",
        role="debate",
        singleton=True,
        reads=frozenset({"reports"}),
        writes=frozenset({"debate"}),
        prompts=("debate", "debate.advocate", "debate.skeptic"),
        build=_llm_build(debate_node),
    ),
    "strategist": NodeKind(
        kind="strategist",
        label="Strategist",
        role="decision",
        singleton=True,
        reads=frozenset({"debate", "prior_lessons"}),
        writes=frozenset({"recommendation"}),
        prompts=("strategist",),
        build=_llm_build(strategist_node),
        router=route_after_strategist,
        router_targets={"judge": "judge", END: END},
    ),
    "judge": NodeKind(
        kind="judge",
        label="Judge",
        role="decision",
        singleton=True,
        reads=frozenset({"recommendation"}),
        writes=frozenset({"judgment", "judge_attempts"}),
        prompts=("judge",),
        build=_llm_build(judge_node),
        router=route_after_judge,
        router_targets={"strategist": "strategist", "risk": "risk"},
    ),
    "risk": NodeKind(
        kind="risk",
        label="Risk",
        role="risk",
        singleton=True,
        reads=frozenset({"recommendation"}),
        writes=frozenset({"risks"}),
        prompts=("risk",),
        build=_llm_build(risk_node),
    ),
    "governance": NodeKind(
        kind="governance",
        label="Governance",
        role="governance",
        singleton=True,
        reads=frozenset({"recommendation", "risks"}),
        writes=frozenset({"governance"}),
        prompts=("governance",),
        build=lambda ctx, config: partial(governance_node, model=ctx.model, ctx=ctx),
    ),
}

PLACEABLE: tuple[str, ...] = tuple(KIND_REGISTRY)
