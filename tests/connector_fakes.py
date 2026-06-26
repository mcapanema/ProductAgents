"""Test doubles for the connector framework.

``FakeSink`` is the connector analogue of ``FakeChatModel``: it satisfies the
``CanonicalSink`` Protocol over an in-memory list, so a connector's ``sync`` can
be tested with no database.
"""

from collections.abc import Iterable

from productagents.core.models import CanonicalModel


class FakeSink:
    """A ``CanonicalSink`` that records every written model."""

    def __init__(self) -> None:
        self.written: list[CanonicalModel] = []

    async def write(self, model: CanonicalModel) -> None:
        self.written.append(model)

    async def write_many(self, models: Iterable[CanonicalModel]) -> None:
        self.written.extend(models)
