"""Platform seam for out-of-graph outcome reflection (re-exports the agent fn).

Permanent presentation seam: lets pa-app reach out-of-graph reflection without
importing pa-agents (forbidden by the layer contract).
"""

from productagents.agents.reflection import reflect

__all__ = ["reflect"]
