"""LangGraph assembly: parallel analysts → debate → strategist → risk → governance."""

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from productagents.agents.context import AgentContext
from productagents.agents.default_workflow import default_definition
from productagents.agents.human_approval import human_approval_node
from productagents.agents.node_kinds import KIND_REGISTRY
from productagents.core.models import (
    END_ID,
    START_ID,
    AnalystReport,
    DebateTurn,
    Evidence,
    GovernanceVerdict,
    Initiative,
    JudgeVerdict,
    Recommendation,
    RiskAssessment,
    WorkflowDefinition,
)
from productagents.core.observability import span


def _traced(name: str, fn):
    """Wrap a node callable so each invocation logs a ``decision.<name>`` span.

    LangGraph passes the state (and sometimes a runtime/config arg); the wrapper
    forwards everything verbatim and returns the node's partial-state dict. Nodes
    degrade internally, so ``status`` is almost always ``ok`` — the value here is
    per-node ``duration_ms``. ponytail: flat log lines, not nested OTel spans;
    when a collector exists, ``span``'s body changes, not these call sites.
    """

    async def traced(state, *args, **kwargs):
        with span(f"decision.{name}"):
            return await fn(state, *args, **kwargs)

    return traced


class GraphState(TypedDict):
    initiative: Initiative
    evidence: Evidence
    reports: Annotated[list[AnalystReport], operator.add]
    debate: list[DebateTurn]
    recommendation: Recommendation | None
    risks: list[RiskAssessment]
    prior_lessons: list[str]
    governance: GovernanceVerdict | None
    judgment: JudgeVerdict | None
    judge_attempts: int


def build_graph_from_definition(
    defn: WorkflowDefinition,
    model_or_context,
    *,
    human_in_the_loop: bool = False,
):
    """Compile a workflow definition into a runnable LangGraph.

    Each node is built by its kind (``KIND_REGISTRY``); conditional kinds
    (strategist/judge) own their routing, so the builder skips their plain
    out-edges and wires ``add_conditional_edges`` from ``kind.router_targets``.
    ``human_in_the_loop`` appends the builder-managed ``human_approval`` node
    exactly as the old ``build_graph`` did (HITL is not a placeable kind).
    """
    ctx = (
        model_or_context
        if isinstance(model_or_context, AgentContext)
        else AgentContext(model=model_or_context)
    )

    # NOTE: GraphState is a valid TypedDict; langgraph's StateT bound stub is
    # too narrow to recognize it. Suppress narrowly rather than weakening the type.
    graph = StateGraph(GraphState)  # ty: ignore[invalid-argument-type]
    for node in defn.nodes:
        kind = KIND_REGISTRY[node.kind]
        graph.add_node(node.id, _traced(node.id, kind.build(ctx, node.config)))

    # Nodes whose out-edges are owned by a router (or by the HITL chain).
    routed = {n.id for n in defn.nodes if KIND_REGISTRY[n.kind].router is not None}
    if human_in_the_loop:
        routed.add("governance")

    for node in defn.nodes:
        kind = KIND_REGISTRY[node.kind]
        if kind.router is not None:
            graph.add_conditional_edges(node.id, kind.router, kind.router_targets)

    for edge in defn.edges:
        if edge.source in routed:
            continue  # router / HITL chain owns this
        src = START if edge.source == START_ID else edge.source
        tgt = END if edge.target == END_ID else edge.target
        graph.add_edge(src, tgt)

    if human_in_the_loop:
        graph.add_node("human_approval", human_approval_node)
        graph.add_edge("governance", "human_approval")
        graph.add_edge("human_approval", END)
        return graph.compile(checkpointer=InMemorySaver())

    return graph.compile()


def build_graph(model_or_context, *, human_in_the_loop: bool = False):
    """Compile the built-in default pipeline (the current graph, as data)."""
    return build_graph_from_definition(
        default_definition(), model_or_context, human_in_the_loop=human_in_the_loop
    )
