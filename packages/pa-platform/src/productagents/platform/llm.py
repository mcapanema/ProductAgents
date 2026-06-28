"""Platform seam for model construction (re-exports the provider-agnostic factory).

# ponytail: thin re-export; gets a proper home in a later phase
"""

from productagents.agents.llm import DEFAULT_MODEL, get_model

__all__ = ["DEFAULT_MODEL", "get_model"]
