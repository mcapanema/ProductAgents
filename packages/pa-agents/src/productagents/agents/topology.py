"""Serializable view of the decision graph's structure.

The GUI's Workflows panel renders this; pa-platform re-exposes it through the
``Workflow`` registry (``Workflow.topology``) so presentation never imports
this package directly.
"""

from productagents.agents.context import AgentContext
from productagents.agents.graph import build_graph

# Which prompt-registry names each node renders (see each node's
# ``prompts.render`` call site). Nodes absent here (recall, human_approval,
# __start__, __end__) render no prompt.
NODE_PROMPTS: dict[str, list[str]] = {
    "customer_research": ["customer_research"],
    "product_analytics": ["product_analytics"],
    "market": ["market"],
    "business": ["business"],
    "technical": ["technical"],
    "debate": ["debate", "debate.advocate", "debate.skeptic"],
    "strategist": ["strategist"],
    "judge": ["judge"],
    "risk": ["risk"],
    "governance": ["governance"],
}

# Bundled prompts that legitimately have no graph node: the reflect agent
# (agents/reflection.py) renders "reflection" outside the graph (see
# CLAUDE.md — "the one agent not wired into graph.py"). Checked against
# PromptStore().names() by tests/test_topology.py so a real gap can't hide
# here silently.
_NON_NODE_PROMPTS: set[str] = {"reflection"}


def graph_topology(*, human_in_the_loop: bool = False) -> dict:
    """Nodes + edges of the compiled decision graph as plain JSON-able dicts.

    Builds the real graph with no model — nodes are never invoked at build
    time — so this picture can never drift from ``graph.py``.
    """
    compiled = build_graph(
        AgentContext(model=None), human_in_the_loop=human_in_the_loop
    )
    drawable = compiled.get_graph()
    return {
        "nodes": [
            {"id": node_id, "prompts": NODE_PROMPTS.get(node_id, [])}
            for node_id in drawable.nodes
        ],
        "edges": [
            {
                "source": e.source,
                "target": e.target,
                "conditional": bool(e.conditional),
            }
            for e in drawable.edges
        ],
    }
