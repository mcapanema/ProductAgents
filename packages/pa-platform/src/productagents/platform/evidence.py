"""Platform seam for evidence resolution (re-exports the agents collector).

# ponytail: thin re-export; gets a proper EvidenceService home in a later phase
"""

from productagents.agents.evidence import EvidenceError, collect_evidence, load_scenario

__all__ = ["EvidenceError", "collect_evidence", "load_scenario"]
