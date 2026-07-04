"""build_graph_from_definition compiles a definition; the default matches graph.py."""

from productagents.agents.default_workflow import default_definition
from productagents.agents.graph import build_graph, build_graph_from_definition
from productagents.core.models import (
    END_ID,
    START_ID,
    WorkflowDefinition,
    WorkflowEdgeDef,
    WorkflowNodeDef,
)
from tests.fakes import FakeChatModel


def _topo(compiled):
    g = compiled.get_graph()
    return (
        set(g.nodes),
        {(e.source, e.target) for e in g.edges},
    )


_ANALYSTS = [
    "customer_research",
    "product_analytics",
    "market",
    "business",
    "technical",
]

# Independently-written expected topology for the pipeline: 5 analysts + recall
# fan out from START; each analyst also edges to debate (recall does not — it
# feeds strategist purely through state, no graph edge); debate -> strategist;
# strategist/judge are conditional routers (strategist: judge on success, END
# on failure; judge: risk on pass/exhausted retries, back to strategist on
# retry); risk -> governance -> END. Nodes with no explicit outgoing edge
# (recall) get an implicit edge to END from langgraph. This is hardcoded from
# the current real pipeline shape, not derived by calling build_graph() or
# default_definition() again, so it catches silent drift in either.
_EXPECTED_NODES = {
    *_ANALYSTS,
    "recall",
    "debate",
    "strategist",
    "judge",
    "risk",
    "governance",
}
_EXPECTED_EDGES = {
    *(("__start__", a) for a in _ANALYSTS),
    ("__start__", "recall"),
    *((a, "debate") for a in _ANALYSTS),  # each analyst fans into debate
    ("recall", "__end__"),  # no outgoing edge in the definition -> implicit finish
    ("debate", "strategist"),
    ("strategist", "judge"),  # conditional: success path
    ("strategist", "__end__"),  # conditional: strategist gave up -> fail fast
    ("judge", "risk"),  # conditional: pass or retries exhausted
    ("judge", "strategist"),  # conditional: retry back-edge
    ("risk", "governance"),
    ("governance", "__end__"),
}


def test_default_definition_matches_the_literal_expected_pipeline_topology():
    model = FakeChatModel({})
    compiled = build_graph_from_definition(default_definition(), model)
    nodes, edges = _topo(compiled)
    assert nodes == _EXPECTED_NODES | {"__start__", "__end__"}
    assert edges == _EXPECTED_EDGES

    # Cheap sanity check IN ADDITION to the literal comparison above: the
    # build_graph() wrapper must delegate to the same builder + definition.
    assert _topo(build_graph(model)) == _topo(compiled)


def test_hitl_appends_human_approval_via_the_builder():
    model = FakeChatModel({})
    compiled = build_graph_from_definition(
        default_definition(), model, human_in_the_loop=True
    )
    nodes, edges = _topo(compiled)
    assert "human_approval" in nodes
    assert ("governance", "human_approval") in edges


def test_hitl_splices_before_whichever_node_is_actually_terminal():
    # Regression for the finding: the HITL splice used to hardcode
    # governance -> human_approval, so a definition with no governance node
    # (any of the other 10 kinds may legitimately be terminal in a
    # user-built workflow) crashed with "edge starting at unknown node
    # 'governance'". The splice must generalize to whatever node(s) the
    # definition actually points at END.
    defn = WorkflowDefinition(
        name="ends_at_risk",
        title="Ends At Risk",
        nodes=[WorkflowNodeDef(id="risk", kind="risk")],
        edges=[
            WorkflowEdgeDef(source=START_ID, target="risk"),
            WorkflowEdgeDef(source="risk", target=END_ID),
        ],
    )
    model = FakeChatModel({})
    compiled = build_graph_from_definition(defn, model, human_in_the_loop=True)
    nodes, edges = _topo(compiled)

    assert "governance" not in nodes
    assert "human_approval" in nodes
    assert ("risk", "human_approval") in edges
    assert ("human_approval", "__end__") in edges
    assert not any(source == "governance" for source, _ in edges)


def test_conditional_kinds_route_through_their_kind_router():
    # A definition without judge: strategist's router still resolves (fail->END,
    # pass->'judge' which is absent) — the builder must not raise at compile time
    # for the present-node case; here we just assert the default compiles.
    compiled = build_graph_from_definition(default_definition(), FakeChatModel({}))
    _nodes, edges = _topo(compiled)
    # judge's back-edge to strategist exists (conditional)
    assert ("judge", "strategist") in edges
    assert ("strategist", "judge") in edges
