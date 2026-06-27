"""Re-export of the shared ``span()`` shim.

``span()`` moved to ``pa-core`` so the agent graph (which may not import
``pa-connectors``) can trace decision runs too. Connector call sites still import
``span`` from here / from ``productagents.connectors``; nothing in this layer changed.
"""

from productagents.core.observability import span

__all__ = ["span"]
