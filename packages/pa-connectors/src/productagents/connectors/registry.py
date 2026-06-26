"""Connector discovery via Python entry points.

Connectors register under the ``productagents.connectors`` group, so a
third-party ``pip install productagents-connector-foo`` adds one with zero
platform changes. Entry points are metadata-only: enumerating them does not
import a connector's httpx/SDK deps until it is actually loaded.
"""

from importlib.metadata import entry_points

from productagents.connectors.base import Connector

_GROUP = "productagents.connectors"


def discover() -> dict[str, type[Connector]]:
    """Map every installed connector's ``key`` to its class."""
    found: dict[str, type[Connector]] = {}
    for ep in entry_points(group=_GROUP):
        cls: type[Connector] = ep.load()
        found[getattr(cls, "key", ep.name)] = cls
    return found
