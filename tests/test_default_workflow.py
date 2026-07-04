"""default_definition() must mirror the current hardcoded graph, as data."""

from productagents.agents.default_workflow import default_definition
from productagents.core.models import END_ID, START_ID


def test_default_has_the_current_nodes():
    defn = default_definition()
    assert defn.name == "evaluate_initiative"
    assert defn.title == "Evaluate Initiative"
    assert defn.builtin is True
    ids = {n.id for n in defn.nodes}
    assert ids == {
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
    # instance id == kind for every default node
    assert all(n.id == n.kind for n in defn.nodes)


def test_default_edges_match_the_current_wiring():
    defn = default_definition()
    edges = {(e.source, e.target) for e in defn.edges}
    analysts = [
        "customer_research",
        "product_analytics",
        "market",
        "business",
        "technical",
    ]
    for a in analysts:
        assert (START_ID, a) in edges
        assert (a, "debate") in edges
    assert (START_ID, "recall") in edges
    # recall has no out-edge (cross-branch prior_lessons, like graph.py)
    assert not any(e.source == "recall" for e in defn.edges)
    assert ("debate", "strategist") in edges
    assert ("strategist", "judge") in edges
    assert ("judge", "risk") in edges
    assert ("risk", "governance") in edges
    assert ("governance", END_ID) in edges


def test_strategist_and_judge_out_edges_flagged_conditional():
    defn = default_definition()
    by_pair = {(e.source, e.target): e.conditional for e in defn.edges}
    assert by_pair[("strategist", "judge")] is True
    assert by_pair[("judge", "risk")] is True
    assert by_pair[("risk", "governance")] is False
