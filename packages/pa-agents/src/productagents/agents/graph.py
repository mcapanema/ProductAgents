"""LangGraph assembly: parallel analysts → debate → strategist → risk → governance."""

import operator
from functools import partial
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from productagents.agents.business import business_node
from productagents.agents.context import AgentContext
from productagents.agents.customer_research import customer_research_node
from productagents.agents.debate import debate_node
from productagents.agents.governance import governance_node
from productagents.agents.human_approval import human_approval_node
from productagents.agents.judge import get_judge_max_retries, judge_node
from productagents.agents.market import market_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.recall import recall_node
from productagents.agents.risk import risk_node
from productagents.agents.strategist import strategist_node
from productagents.agents.technical import technical_node
from productagents.core.models import (
    AnalystReport,
    DebateTurn,
    DecisionRecord,
    Evidence,
    GovernanceVerdict,
    Initiative,
    JudgeVerdict,
    OutcomeRecord,
    Recommendation,
    RiskAssessment,
)


class GraphState(TypedDict):
    initiative: Initiative
    evidence: Evidence
    reports: Annotated[list[AnalystReport], operator.add]
    debate: list[DebateTurn]
    recommendation: Recommendation | None
    risks: list[RiskAssessment]
    portfolio: list[DecisionRecord]
    outcomes: list[OutcomeRecord]
    prior_lessons: list[str]
    governance: GovernanceVerdict | None
    judgment: JudgeVerdict | None
    judge_attempts: int


def _route_after_strategist(state) -> str:
    """Fail fast: end the run when the strategist could not produce a rec."""
    recommendation = state.get("recommendation")
    if recommendation is None or recommendation.failed:
        return END
    return "judge"


def _route_after_judge(state) -> str:
    """Route forward to risk on pass/exhausted retries, else back to strategist."""
    judgment = state.get("judgment")
    if judgment is None or judgment.passed:
        return "risk"
    if state.get("judge_attempts", 0) > get_judge_max_retries():
        return "risk"
    return "strategist"


def build_graph(model, *, human_in_the_loop: bool = False):
    """Compile the decision graph using the injected chat model.

    When `human_in_the_loop` is True, a `human_approval` node is appended after
    `governance` (whose verdict becomes advisory) and the graph is compiled with
    an in-memory checkpointer so it can pause on `interrupt()` and resume.
    """
    # NOTE: GraphState is a valid TypedDict; langgraph's StateT bound stub is
    # too narrow to recognize it. Suppress narrowly rather than weakening the type.
    graph = StateGraph(GraphState)  # ty: ignore[invalid-argument-type]
    ctx = AgentContext(
        model=model
    )  # ponytail: bare model → context; Task 5 adds service fields
    graph.add_node("customer_research", partial(customer_research_node, ctx=ctx))
    graph.add_node("product_analytics", partial(product_analytics_node, ctx=ctx))
    graph.add_node("market", partial(market_node, ctx=ctx))
    graph.add_node("business", partial(business_node, ctx=ctx))
    graph.add_node("technical", partial(technical_node, ctx=ctx))
    graph.add_node("recall", recall_node)
    graph.add_node("debate", partial(debate_node, model=model))
    graph.add_node("strategist", partial(strategist_node, model=model))
    graph.add_node("judge", partial(judge_node, model=model))
    graph.add_node("risk", partial(risk_node, model=model))
    graph.add_node("governance", partial(governance_node, model=model))

    graph.add_edge(START, "customer_research")
    graph.add_edge(START, "product_analytics")
    graph.add_edge(START, "market")
    graph.add_edge(START, "business")
    graph.add_edge(START, "technical")
    graph.add_edge(START, "recall")
    graph.add_edge("customer_research", "debate")
    graph.add_edge("product_analytics", "debate")
    graph.add_edge("market", "debate")
    graph.add_edge("business", "debate")
    graph.add_edge("technical", "debate")
    graph.add_edge("debate", "strategist")
    graph.add_conditional_edges(
        "strategist",
        _route_after_strategist,
        {"judge": "judge", END: END},
    )
    graph.add_conditional_edges(
        "judge",
        _route_after_judge,
        {"strategist": "strategist", "risk": "risk"},
    )
    graph.add_edge("risk", "governance")

    if human_in_the_loop:
        graph.add_node("human_approval", human_approval_node)
        graph.add_edge("governance", "human_approval")
        graph.add_edge("human_approval", END)
        return graph.compile(checkpointer=InMemorySaver())

    graph.add_edge("governance", END)
    return graph.compile()
