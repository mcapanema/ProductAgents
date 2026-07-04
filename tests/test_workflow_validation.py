"""validate_definition — the always-runnable guarantee."""

from productagents.agents.default_workflow import default_definition
from productagents.agents.workflow_validation import validate_definition
from productagents.core.models import (
    END_ID,
    START_ID,
    WorkflowDefinition,
    WorkflowEdgeDef,
    WorkflowNodeDef,
)


def test_default_definition_is_valid():
    assert validate_definition(default_definition()) == []


def test_unknown_kind_is_rejected():
    defn = WorkflowDefinition(
        name="x",
        title="X",
        nodes=[WorkflowNodeDef(id="n", kind="nope")],
        edges=[
            WorkflowEdgeDef(source=START_ID, target="n"),
            WorkflowEdgeDef(source="n", target=END_ID),
        ],
    )
    errs = validate_definition(defn)
    assert any("unknown kind" in e.lower() for e in errs)


def test_missing_upstream_input_is_rejected():
    # judge reads 'recommendation' but nothing upstream writes it
    defn = WorkflowDefinition(
        name="x",
        title="X",
        nodes=[WorkflowNodeDef(id="judge", kind="judge")],
        edges=[
            WorkflowEdgeDef(source=START_ID, target="judge"),
            WorkflowEdgeDef(source="judge", target=END_ID),
        ],
    )
    errs = validate_definition(defn)
    assert any("recommendation" in e for e in errs)


def test_duplicate_singleton_is_rejected():
    defn = WorkflowDefinition(
        name="x",
        title="X",
        nodes=[
            WorkflowNodeDef(id="debate", kind="debate"),
            WorkflowNodeDef(id="debate#2", kind="debate"),
        ],
        edges=[],
    )
    errs = validate_definition(defn)
    assert any("singleton" in e.lower() for e in errs)


def test_duplicate_analyst_is_allowed():
    # two market instances fanning into debate is legal
    defn = WorkflowDefinition(
        name="x",
        title="X",
        nodes=[
            WorkflowNodeDef(id="market", kind="market"),
            WorkflowNodeDef(id="market#2", kind="market"),
            WorkflowNodeDef(id="debate", kind="debate"),
        ],
        edges=[
            WorkflowEdgeDef(source=START_ID, target="market"),
            WorkflowEdgeDef(source=START_ID, target="market#2"),
            WorkflowEdgeDef(source="market", target="debate"),
            WorkflowEdgeDef(source="market#2", target="debate"),
            WorkflowEdgeDef(source="debate", target=END_ID),
        ],
    )
    assert validate_definition(defn) == []


def test_unknown_edge_endpoint_is_rejected():
    defn = WorkflowDefinition(
        name="x",
        title="X",
        nodes=[WorkflowNodeDef(id="market", kind="market")],
        edges=[WorkflowEdgeDef(source=START_ID, target="ghost")],
    )
    errs = validate_definition(defn)
    assert any("ghost" in e for e in errs)


def test_unreachable_node_is_rejected():
    # market->debate is a valid connected pair; business has no edges at all
    defn = WorkflowDefinition(
        name="x",
        title="X",
        nodes=[
            WorkflowNodeDef(id="market", kind="market"),
            WorkflowNodeDef(id="debate", kind="debate"),
            WorkflowNodeDef(id="business", kind="business"),
        ],
        edges=[
            WorkflowEdgeDef(source=START_ID, target="market"),
            WorkflowEdgeDef(source="market", target="debate"),
            WorkflowEdgeDef(source="debate", target=END_ID),
        ],
    )
    errs = validate_definition(defn)
    assert any("unreachable" in e for e in errs)


def test_cycle_in_forward_edges_is_rejected():
    defn = WorkflowDefinition(
        name="x",
        title="X",
        nodes=[
            WorkflowNodeDef(id="market", kind="market"),
            WorkflowNodeDef(id="debate", kind="debate"),
        ],
        edges=[
            WorkflowEdgeDef(source="market", target="debate"),
            WorkflowEdgeDef(source="debate", target="market"),
        ],
    )
    errs = validate_definition(defn)
    assert any("cycle" in e.lower() for e in errs)
