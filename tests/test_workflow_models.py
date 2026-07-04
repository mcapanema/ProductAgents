"""WorkflowDefinition — the persisted, editable data form of a pipeline."""

from productagents.core.models import (
    END_ID,
    START_ID,
    WorkflowDefinition,
    WorkflowEdgeDef,
    WorkflowNodeDef,
)


def test_definition_roundtrips_through_json():
    defn = WorkflowDefinition(
        name="demo",
        title="Demo",
        nodes=[WorkflowNodeDef(id="market", kind="market")],
        edges=[WorkflowEdgeDef(source=START_ID, target="market")],
        layout={"market": (10.0, 20.0)},
    )
    restored = WorkflowDefinition.model_validate(defn.model_dump(mode="json"))
    assert restored == defn
    assert restored.nodes[0].config == {}
    assert restored.edges[0].conditional is False
    assert (START_ID, END_ID) == ("__start__", "__end__")


def test_node_and_edge_defaults():
    node = WorkflowNodeDef(id="debate", kind="debate")
    edge = WorkflowEdgeDef(source="debate", target="strategist")
    assert node.config == {}
    assert edge.conditional is False
