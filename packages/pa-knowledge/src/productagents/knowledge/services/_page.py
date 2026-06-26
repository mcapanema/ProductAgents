"""Typed pagination result returned by every knowledge-service query.

Carries the slice plus the metadata an agent needs to decide whether to keep
reading (``total``, ``has_more``). Generic over the canonical type it pages.
"""

from pydantic import BaseModel


class Page[T](BaseModel):
    """A page of query results plus paging metadata."""

    items: list[T]
    total: int  # total matches across all pages, before limit/offset
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        """True when matches remain beyond this page."""
        return self.offset + len(self.items) < self.total

    @classmethod
    def paginate(cls, items: list[T], *, limit: int, offset: int) -> Page[T]:
        """Slice an already-matched list into a single page."""
        window = items[offset : offset + limit]
        return cls(items=window, total=len(items), limit=limit, offset=offset)
