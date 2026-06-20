"""LangGraph assembly: parallel analysts → debate → strategist → risk → governance."""

import operator
from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from productagents.agents.business import business_node
from productagents.agents.customer_research import customer_research_node
from productagents.agents.debate import debate_node
from productagents.agents.governance import governance_node
from productagents.agents.market import market_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.recall import recall_node
from productagents.agents.risk import risk_node
from productagents.agents.strategist import strategist_node
from productagents.agents.technical import technical_node
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    DecisionRecord,
    Evidence,
    GovernanceVerdict,
    Initiative,
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


def build_graph(model):
    """Compile the decision graph using the injected chat model."""
    # NOTE: GraphState is a valid TypedDict; langgraph's StateT bound stub is
    # too narrow to recognize it. Suppress narrowly rather than weakening the type.
    graph = StateGraph(GraphState)  # ty: ignore[invalid-argument-type]
    graph.add_node("customer_research", partial(customer_research_node, model=model))
    graph.add_node("product_analytics", partial(product_analytics_node, model=model))
    graph.add_node("market", partial(market_node, model=model))
    graph.add_node("business", partial(business_node, model=model))
    graph.add_node("technical", partial(technical_node, model=model))
    graph.add_node("recall", recall_node)
    graph.add_node("debate", partial(debate_node, model=model))
    graph.add_node("strategist", partial(strategist_node, model=model))
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
    graph.add_edge("strategist", "risk")
    graph.add_edge("risk", "governance")
    graph.add_edge("governance", END)

    return graph.compile()
