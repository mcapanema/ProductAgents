"""The shared, provider-agnostic async HTTP layer for connectors.

One place owns timeouts, bearer auth, and transient-error retry so every
connector inherits the same resilience. Transient detection delegates to
``connector_errors`` (the single source of truth for which statuses are worth
retrying).
"""

import asyncio
import logging
from typing import Any

import httpx

from productagents.connectors.connector_errors import is_transient_status

logger = logging.getLogger("productagents.connectors")


def make_client(
    *,
    base_url: str,
    token: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> httpx.AsyncClient:
    """Build an ``AsyncClient`` with optional bearer auth + default headers."""
    merged = dict(headers or {})
    if token:
        merged["Authorization"] = f"Bearer {token}"
    return httpx.AsyncClient(base_url=base_url, headers=merged, timeout=timeout)


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    base_delay: float = 0.5,
    **kwargs: Any,
) -> httpx.Response:
    """Issue a request, retrying transient transport/status errors with backoff.

    Raises ``httpx.HTTPStatusError`` on a non-transient ``4xx``/``5xx`` (or after
    the retry budget is spent); raises the transport error if connecting keeps
    failing. The caller (a connector) turns that into a degraded ``SyncResult``.
    """
    for attempt in range(max_retries + 1):
        last = attempt == max_retries
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.TransportError:
            if last:
                raise
        else:
            if is_transient_status(response.status_code) and not last:
                logger.warning(
                    "http retry method=%s url=%s status=%d attempt=%d",
                    method,
                    url,
                    response.status_code,
                    attempt,
                )
                await asyncio.sleep(base_delay * (2**attempt))
                continue
            response.raise_for_status()
            return response
        await asyncio.sleep(base_delay * (2**attempt))
    raise AssertionError("unreachable: loop returns or raises on the last attempt")
