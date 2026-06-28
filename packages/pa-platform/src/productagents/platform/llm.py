"""Platform seam for model construction (re-exports the provider-agnostic factory).

# ponytail: thin re-export; gets a proper home in a later phase
"""

from productagents.agents.llm import get_model

__all__ = ["get_model"]
