"""Platform seam for out-of-graph outcome reflection (re-exports the agent fn).

# ponytail: thin re-export; gets a proper ReflectionService home in a later phase
"""

from productagents.agents.reflection import reflect

__all__ = ["reflect"]
