"""Shared query engine for every knowledge service: get-by-id + filtered search.

One implementation serves all services; concrete services are thin named
subclasses parametrized by canonical type.
"""

from productagents.core.models import CanonicalModel
from productagents.knowledge.repositories._base import Repository
from productagents.knowledge.services._page import Page
from productagents.knowledge.services._query import Query

# ponytail: search scans the full type partition then filters/paginates in
# Python. Correct and cheap at local-first SQLite scale (no connectors yet,
# hundreds of rows). When a connector turns a partition into a real table, push
# the predicate down into the repository (add a `find` method) instead of
# widening this scan limit.
_SCAN_LIMIT = 10_000


class CanonicalQueryService[T: CanonicalModel]:
    """Get-by-id and typed, paginated search over one canonical type."""

    def __init__(self, repo: Repository[T]) -> None:
        self._repo = repo

    async def get(self, id: str) -> T | None:
        return await self._repo.get(id)

    async def search(self, query: Query[T]) -> Page[T]:
        rows = await self._repo.list(limit=_SCAN_LIMIT, offset=0)
        matched = [row for row in rows if query.matches(row)]
        return Page.paginate(matched, limit=query.limit, offset=query.offset)
