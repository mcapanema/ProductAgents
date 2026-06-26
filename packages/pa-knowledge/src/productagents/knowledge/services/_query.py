"""Base for typed service queries: paging knobs + a pure match predicate.

A query is a pydantic model so the agent↔service contract is introspectable and
stable (typed fields, not kwargs soup). The base contributes ``limit``/``offset``
and a match-everything default; each service subclasses it, adds filter fields,
and overrides ``matches``.
"""

from pydantic import BaseModel

from productagents.core.models import CanonicalModel


class Query[T: CanonicalModel](BaseModel):
    """A typed, paginated query over one canonical type."""

    limit: int = 50
    offset: int = 0

    def matches(self, model: T) -> bool:
        """Return True if ``model`` satisfies this query. Default: match all."""
        return True
