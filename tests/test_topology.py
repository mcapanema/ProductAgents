"""Topology derives from a WorkflowDefinition, not a compiled graph."""

from productagents.agents.default_workflow import default_definition
from productagents.agents.topology import definition_topology, graph_topology


def test_definition_topology_carries_kind_and_prompts():
    topo = definition_topology(default_definition())
    by_id = {n["id"]: n for n in topo["nodes"]}
    assert by_id["market"]["kind"] == "market"
    assert by_id["market"]["prompts"] == ["market"]
    assert by_id["debate"]["prompts"] == ["debate", "debate.advocate", "debate.skeptic"]
    assert by_id["recall"]["prompts"] == []


def test_edges_flag_conditional():
    topo = definition_topology(default_definition())
    pairs = {(e["source"], e["target"]): e["conditional"] for e in topo["edges"]}
    assert pairs[("strategist", "judge")] is True
    assert pairs[("risk", "governance")] is False
    assert pairs[("__start__", "market")] is False


def test_graph_topology_delegates_to_the_default():
    assert graph_topology() == definition_topology(default_definition())


def test_topology_human_in_the_loop_adds_approval_node():
    topo = definition_topology(default_definition(), human_in_the_loop=True)
    ids = {n["id"] for n in topo["nodes"]}
    assert "human_approval" in ids
    pairs = {(e["source"], e["target"]) for e in topo["edges"]}
    assert ("governance", "human_approval") in pairs
    assert ("human_approval", "__end__") in pairs
    assert ("governance", "__end__") not in pairs

    graph_topo = graph_topology(human_in_the_loop=True)
    assert graph_topo == topo
