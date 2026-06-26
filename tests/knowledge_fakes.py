"""In-memory test doubles for the knowledge layer.

``FakeRepository`` implements the ``Repository[T]`` protocol over a dict so
services can be unit-tested with no database — the storage analogue of
``FakeChatModel``.
"""

from productagents.core.models import CanonicalModel


class FakeRepository[T: CanonicalModel]:
    """A ``Repository[T]`` backed by an insertion-ordered dict."""

    def __init__(self, items: list[T] | None = None) -> None:  # ty: ignore[invalid-type-form]  # shadowed-builtin
        self._items: dict[str, T] = {str(m.id): m for m in (items or [])}

    async def get(self, id: str) -> T | None:
        return self._items.get(str(id))

    async def upsert(self, model: T) -> T:
        self._items[str(model.id)] = model
        return model

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[T]:  # ty: ignore[invalid-type-form]  # shadowed-builtin
        values = list(self._items.values())
        return values[offset : offset + limit]
