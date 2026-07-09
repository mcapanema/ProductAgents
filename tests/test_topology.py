"""Tests for the serializable graph-topology accessor."""

from productagents.agents.prompts import PromptStore
from productagents.agents.topology import (
    _NON_NODE_PROMPTS,
    NODE_PROMPTS,
    graph_topology,
)


def _node_ids(topo: dict) -> list[str]:
    return [n["id"] for n in topo["nodes"]]


def test_topology_lists_all_pipeline_nodes():
    topo = graph_topology()
    ids = _node_ids(topo)
    for expected in (
        "__start__",
        "__end__",
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
    ):
        assert expected in ids
    assert "human_approval" not in ids


def test_topology_human_in_the_loop_adds_approval_node():
    assert "human_approval" in _node_ids(graph_topology(human_in_the_loop=True))


def test_topology_marks_conditional_edges():
    topo = graph_topology()
    edges = {(e["source"], e["target"]): e["conditional"] for e in topo["edges"]}
    assert edges[("judge", "strategist")] is True
    assert edges[("judge", "risk")] is True
    assert edges[("debate", "strategist")] is False
    assert edges[("risk", "governance")] is False


def test_topology_maps_nodes_to_their_prompts():
    topo = graph_topology()
    prompts = {n["id"]: n["prompts"] for n in topo["nodes"]}
    assert prompts["strategist"] == ["strategist"]
    assert prompts["debate"] == ["debate", "debate.advocate", "debate.skeptic"]
    assert prompts["recall"] == []
    assert prompts["__start__"] == []


def test_every_bundled_prompt_is_mapped_in_topology():
    """Guard against NODE_PROMPTS drifting from the real bundled prompt set.

    NODE_PROMPTS is hand-maintained; PromptStore.names() is the source of
    truth. Every bundled prompt must be either wired to a graph node here or
    explicitly allow-listed in _NON_NODE_PROMPTS with a reason.
    """
    bundled = set(PromptStore().names())
    mapped = {name for names in NODE_PROMPTS.values() for name in names}
    unaccounted = bundled - mapped - _NON_NODE_PROMPTS
    assert unaccounted == set()
