"""Workflow definitions: the persisted, editable data form of a decision pipeline.

A ``WorkflowDefinition`` is what the GUI editor mutates and the store persists —
a graph of node *instances* (each naming a registered ``kind``) plus edges. The
node-kind registry and the dynamic builder that turn a definition into a runnable
LangGraph live in pa-agents; pa-core holds only the schema (staying dependency-light).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

START_ID = "__start__"
END_ID = "__end__"


class WorkflowNodeDef(BaseModel):
    id: str  # unique instance id within the definition
    kind: str  # a registered node-kind id (see productagents.agents.node_kinds)
    config: dict = Field(default_factory=dict)


class WorkflowEdgeDef(BaseModel):
    source: str  # a node id, or START_ID
    target: str  # a node id, or END_ID
    conditional: bool = False  # display-only; routing is intrinsic to the kind


class WorkflowDefinition(BaseModel):
    name: str  # slug, unique per workspace
    title: str
    description: str = ""
    nodes: list[WorkflowNodeDef] = Field(default_factory=list)
    edges: list[WorkflowEdgeDef] = Field(default_factory=list)
    layout: dict[str, tuple[float, float]] = Field(default_factory=dict)
    builtin: bool = False  # the seeded default: resettable, never deletable
