"""Platform seam for model construction (re-exports the provider-agnostic factory).

Permanent presentation seam: lets pa-app reach the model factory without
importing pa-agents (forbidden by the layer contract).
"""

from productagents.agents.llm import DEFAULT_MAX_RETRIES, DEFAULT_MODEL, get_model

__all__ = ["DEFAULT_MAX_RETRIES", "DEFAULT_MODEL", "get_model"]
