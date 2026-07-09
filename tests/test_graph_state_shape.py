"""Guard test: the runner's initial graph state must match GraphState's shape.

`runner.py::_build_initial_state` and `graph.py::GraphState` are two independent
declarations of the same set of state keys. A key added to one and not the
other is a real bug (a field the graph never sees, or a state key nothing
initializes) — this test catches that drift at import time, no graph run
required.
"""

from productagents.agents.graph import GraphState
from productagents.agents.runner import initial_state_keys


def test_initial_state_matches_graph_state_shape():
    assert set(initial_state_keys()) == set(GraphState.__annotations__)
