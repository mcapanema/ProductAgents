"""Concurrent sync orchestration over enabled connectors.

Each connector runs in its own task under an ``asyncio.TaskGroup``. Every run is
wrapped so an exception becomes a degraded ``SyncResult`` instead of propagating
— a raised exception inside a TaskGroup would cancel its siblings, which would
break the degrade-don't-crash contract. So ``_run_one`` never raises.

ponytail: cursors are threaded in and returned, not persisted between processes.
There is no scheduler yet (nothing re-runs a connector), so a ``sync_state``
store is deferred to Phase 7 (observability + config UX), where the scheduler
that needs persisted cursors gets built. Until then, the caller supplies cursors.
"""

import asyncio

from productagents.connectors.base import Connector, SyncCursor, SyncResult


async def _run_one(connector: Connector, cursor: SyncCursor | None) -> SyncResult:
    """Run one connector's sync, degrading any failure to ``ok=False``."""
    try:
        return await connector.sync(cursor)
    except Exception as exc:  # noqa: BLE001 — degrade-don't-crash is the contract
        return SyncResult(connector=connector.key, ok=False, error=str(exc))


async def run_sync(
    connectors: list[Connector],
    cursors: dict[str, SyncCursor | None] | None = None,
) -> list[SyncResult]:
    """Sync every connector concurrently; return results in input order."""
    cursors = cursors or {}
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_run_one(c, cursors.get(c.key))) for c in connectors]
    return [t.result() for t in tasks]
