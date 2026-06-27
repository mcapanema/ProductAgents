"""Concurrent sync orchestration over enabled connectors.

Each connector runs in its own task under an ``asyncio.TaskGroup``. Every run is
wrapped so an exception becomes a degraded ``SyncResult`` instead of propagating
— a raised exception inside a TaskGroup would cancel its siblings, which would
break the degrade-don't-crash contract. So ``_run_one`` never raises.

Each run is wrapped in a ``connector.sync`` span (``observability.span``) so its
duration, write count, and outcome land in the log; a raised failure is run
through ``connector_errors`` for a categorized, friendly ``SyncResult.error``.
ponytail: cursors are threaded in and returned by the caller (``app/sync.py``
persists them); there is still no in-process scheduler.
"""

import asyncio

from productagents.connectors.base import Connector, SyncCursor, SyncResult
from productagents.connectors.connector_errors import classify_connector_error
from productagents.connectors.observability import span


async def _run_one(connector: Connector, cursor: SyncCursor | None) -> SyncResult:
    """Run one connector's sync inside a span, degrading any failure to ok=False."""
    with span("connector.sync", connector=connector.key) as attrs:
        try:
            result = await connector.sync(cursor)
        except Exception as exc:  # noqa: BLE001 — degrade-don't-crash is the contract
            info = classify_connector_error(exc)
            attrs["status"] = "error"
            attrs["category"] = info.category
            return SyncResult(connector=connector.key, ok=False, error=str(info))
        attrs["written"] = result.written
        if not result.ok:
            attrs["status"] = "error"
        return result


async def run_sync(
    connectors: list[Connector],
    cursors: dict[str, SyncCursor | None] | None = None,
) -> list[SyncResult]:
    """Sync every connector concurrently; return results in input order."""
    cursors = cursors or {}
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_run_one(c, cursors.get(c.key))) for c in connectors]
    return [t.result() for t in tasks]
