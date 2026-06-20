"""LangGraph assembly: parallel analysts → debate → strategist."""

import operator
from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from productagents.agents.customer_research import customer_research_node
from productagents.agents.debate import debate_node
from productagents.agents.product_analytics import product_analytics_node
from productagents.agents.strategist import strategist_node
from productagents.schemas import (
    AnalystReport,
    DebateTurn,
    Evidence,
    Initiative,
    Recommendation,
)


class GraphState(TypedDict):
    initiative: Initiative
    evidence: Evidence
    reports: Annotated[list[AnalystReport], operator.add]
    debate: list[DebateTurn]
    recommendation: Recommendation | None


def build_graph(model):
    """Compile the decision graph using the injected chat model."""
    graph = StateGraph(GraphState)
    graph.add_node("customer_research", partial(customer_research_node, model=model))
    graph.add_node("product_analytics", partial(product_analytics_node, model=model))
    graph.add_node("debate", partial(debate_node, model=model))
    graph.add_node("strategist", partial(strategist_node, model=model))

    graph.add_edge(START, "customer_research")
    graph.add_edge(START, "product_analytics")
    graph.add_edge("customer_research", "debate")
    graph.add_edge("product_analytics", "debate")
    graph.add_edge("debate", "strategist")
    graph.add_edge("strategist", END)

    return graph.compile()
