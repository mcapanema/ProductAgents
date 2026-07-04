"""Serializable view of a workflow definition's structure (GUI Workflows panel).

Derived directly from the ``WorkflowDefinition`` data (no graph compile needed),
so prompts come from each node's kind and the picture can never drift from the
registry.
"""

from productagents.agents.default_workflow import default_definition
from productagents.agents.node_kinds import KIND_REGISTRY
from productagents.core.models import WorkflowDefinition
from productagents.core.models.workflow import END_ID


def definition_topology(
    defn: WorkflowDefinition, *, human_in_the_loop: bool = False
) -> dict:
    nodes = [
        {
            "id": n.id,
            "kind": n.kind,
            "prompts": list(KIND_REGISTRY[n.kind].prompts)
            if n.kind in KIND_REGISTRY
            else [],
            "config": n.config,
        }
        for n in defn.nodes
    ]
    edges = [
        {"source": e.source, "target": e.target, "conditional": e.conditional}
        for e in defn.edges
    ]
    if human_in_the_loop:
        # Mirrors build_graph_from_definition's HITL wiring: human_approval is
        # builder-managed (not a placeable kind), spliced between whatever
        # used to target END and END itself.
        nodes.append(
            {
                "id": "human_approval",
                "kind": "human_approval",
                "prompts": [],
                "config": {},
            }
        )
        for edge in edges:
            if edge["target"] == END_ID:
                edge["target"] = "human_approval"
        edges.append(
            {"source": "human_approval", "target": END_ID, "conditional": False}
        )
    return {"nodes": nodes, "edges": edges}


def graph_topology(*, human_in_the_loop: bool = False) -> dict:
    """Topology of the built-in default pipeline (back-compat accessor)."""
    return definition_topology(
        default_definition(), human_in_the_loop=human_in_the_loop
    )
