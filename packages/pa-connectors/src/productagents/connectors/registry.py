import logging
from importlib.metadata import entry_points

from productagents.connectors.base import Connector

logger = logging.getLogger("productagents.connectors")

_GROUP = "productagents.connectors"


def discover() -> dict[str, type[Connector]]:
    """Map every installed connector's ``key`` to its class.

    One broken third-party entry point (bad import, renamed class) is logged and
    skipped so it can't take down discovery for every other connector — mirrors
    ``workflow_registry.discover``.
    """
    found: dict[str, type[Connector]] = {}
    for ep in entry_points(group=_GROUP):
        try:
            cls: type[Connector] = ep.load()
        except Exception:  # noqa: BLE001 — a broken plugin must not kill discovery
            logger.warning(
                "connector entry point %r failed to load; skipping",
                ep.name,
                exc_info=True,
            )
            continue
        found[getattr(cls, "key", ep.name)] = cls
    return found
