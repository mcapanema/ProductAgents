"""The built-in default workflow — the current decision pipeline as a definition.

``build_graph`` builds this; the store seeds it. Keeping it here (next to the
registry it references) means the seeded default can never drift from the kinds.
"""

from __future__ import annotations

from productagents.core.models import (
    END_ID,
    START_ID,
    WorkflowDefinition,
    WorkflowEdgeDef,
    WorkflowNodeDef,
)

_ANALYSTS = [
    "customer_research",
    "product_analytics",
    "market",
    "business",
    "technical",
]
_SPINE = ["recall", "debate", "strategist", "judge", "risk", "governance"]


def default_definition() -> WorkflowDefinition:
    nodes = [WorkflowNodeDef(id=k, kind=k) for k in (*_ANALYSTS, *_SPINE)]
    edges = [WorkflowEdgeDef(source=START_ID, target=a) for a in _ANALYSTS]
    edges.append(WorkflowEdgeDef(source=START_ID, target="recall"))
    edges += [WorkflowEdgeDef(source=a, target="debate") for a in _ANALYSTS]
    edges += [
        WorkflowEdgeDef(source="debate", target="strategist"),
        WorkflowEdgeDef(source="strategist", target="judge", conditional=True),
        WorkflowEdgeDef(source="judge", target="risk", conditional=True),
        WorkflowEdgeDef(source="risk", target="governance"),
        WorkflowEdgeDef(source="governance", target=END_ID),
    ]
    return WorkflowDefinition(
        name="evaluate_initiative",
        title="Evaluate Initiative",
        description=(
            "Advisory pipeline: evidence → analysts → debate → "
            "strategist → judge → risk → governance."
        ),
        nodes=nodes,
        edges=edges,
        builtin=True,
    )
