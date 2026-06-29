"""Platform seam for evidence resolution (re-exports the agents collector).

Permanent presentation seam: lets pa-app reach evidence collection without
importing pa-agents (forbidden by the layer contract).
"""

from productagents.agents.evidence import EvidenceError, collect_evidence, load_scenario

__all__ = ["EvidenceError", "collect_evidence", "load_scenario"]
