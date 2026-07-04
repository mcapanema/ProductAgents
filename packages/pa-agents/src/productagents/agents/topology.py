"""Serializable view of a workflow definition's structure (GUI Workflows panel).

Derived directly from the ``WorkflowDefinition`` data (no graph compile needed),
so prompts come from each node's kind and the picture can never drift from the
registry.
"""

from productagents.agents.default_workflow import default_definition
from productagents.agents.node_kinds import KIND_REGISTRY
from productagents.core.models import WorkflowDefinition


def definition_topology(defn: WorkflowDefinition) -> dict:
    return {
        "nodes": [
            {
                "id": n.id,
                "kind": n.kind,
                "prompts": list(KIND_REGISTRY[n.kind].prompts)
                if n.kind in KIND_REGISTRY
                else [],
                "config": n.config,
            }
            for n in defn.nodes
        ],
        "edges": [
            {"source": e.source, "target": e.target, "conditional": e.conditional}
            for e in defn.edges
        ],
    }


def graph_topology(*, human_in_the_loop: bool = False) -> dict:
    """Topology of the built-in default pipeline (back-compat accessor)."""
    return definition_topology(default_definition())
