"""The storage-agnostic repository contract services depend on.

Services (Phase 3) depend on this Protocol, never on a concrete implementation,
so SQLite can be swapped for Postgres — or a fake injected in tests — without a
service change.
"""

from typing import Protocol

from productagents.core.models import CanonicalModel


class Repository[T: CanonicalModel](Protocol):
    """Persist and query canonical entities of a single type."""

    async def get(self, id: str) -> T | None:
        """Return the entity with this platform id, or ``None``."""
        ...

    async def upsert(self, model: T) -> T:
        """Insert or update. Returns the persisted model (its id may be the
        stable id of a pre-existing vendor record). Idempotent on re-sync."""
        ...

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[T]:  # ty: ignore[invalid-type-form]  # shadowed-builtin
        """Return a page of entities of this repository's type."""
        ...
