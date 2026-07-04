"""build_graph_from_definition compiles a definition; the default matches graph.py."""

from productagents.agents.default_workflow import default_definition
from productagents.agents.graph import build_graph, build_graph_from_definition
from tests.fakes import FakeChatModel


def _topo(compiled):
    g = compiled.get_graph()
    return (
        set(g.nodes),
        {(e.source, e.target) for e in g.edges},
    )


def test_default_definition_builds_the_same_graph_as_build_graph():
    model = FakeChatModel({})
    from_defn = build_graph_from_definition(default_definition(), model)
    hardcoded = build_graph(model)
    assert _topo(from_defn) == _topo(hardcoded)


def test_hitl_appends_human_approval_via_the_builder():
    model = FakeChatModel({})
    compiled = build_graph_from_definition(
        default_definition(), model, human_in_the_loop=True
    )
    nodes, edges = _topo(compiled)
    assert "human_approval" in nodes
    assert ("governance", "human_approval") in edges


def test_conditional_kinds_route_through_their_kind_router():
    # A definition without judge: strategist's router still resolves (fail->END,
    # pass->'judge' which is absent) — the builder must not raise at compile time
    # for the present-node case; here we just assert the default compiles.
    compiled = build_graph_from_definition(default_definition(), FakeChatModel({}))
    _nodes, edges = _topo(compiled)
    # judge's back-edge to strategist exists (conditional)
    assert ("judge", "strategist") in edges
    assert ("strategist", "judge") in edges
