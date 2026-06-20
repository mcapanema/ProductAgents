"""LangGraph assembly: parallel analysts → debate → strategist → risk → governance."""

import operator
from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from productagents.agents.customer_research import customer_research_node
from productagents.agents.debate import debate_node
from productagents.agents.governance import governance_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.risk import risk_node
from productagents.agents.strategist import strategist_node
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    DecisionRecord,
    Evidence,
    GovernanceVerdict,
    Initiative,
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
    governance: GovernanceVerdict | None


def build_graph(model):
    """Compile the decision graph using the injected chat model."""
    # NOTE: GraphState is a valid TypedDict; langgraph's StateT bound stub is
    # too narrow to recognize it. Suppress narrowly rather than weakening the type.
    graph = StateGraph(GraphState)  # ty: ignore[invalid-argument-type]
    graph.add_node("customer_research", partial(customer_research_node, model=model))
    graph.add_node("product_analytics", partial(product_analytics_node, model=model))
    graph.add_node("debate", partial(debate_node, model=model))
    graph.add_node("strategist", partial(strategist_node, model=model))
    graph.add_node("risk", partial(risk_node, model=model))
    graph.add_node("governance", partial(governance_node, model=model))

    graph.add_edge(START, "customer_research")
    graph.add_edge(START, "product_analytics")
    graph.add_edge("customer_research", "debate")
    graph.add_edge("product_analytics", "debate")
    graph.add_edge("debate", "strategist")
    graph.add_edge("strategist", "risk")
    graph.add_edge("risk", "governance")
    graph.add_edge("governance", END)

    return graph.compile()
