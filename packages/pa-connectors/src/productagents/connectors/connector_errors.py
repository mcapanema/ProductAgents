"""Provider-agnostic classification of connector (HTTP) failures.

Mirrors ``agents/llm_errors.py`` but for the connector layer. Connectors talk to
vendors over ``httpx``, so — unlike the LLM classifier, which spans many SDKs and
must sniff strings — this one inspects ``httpx`` types directly: an
``HTTPStatusError`` carries a response status; a ``TransportError`` is a
connect/read failure. It maps any exception to a small set of actionable
categories plus a ``transient`` flag that the retry layer and the health surface
both consume. Like its LLM sibling, ``classify_connector_error`` *returns* a
``ConnectorError`` — it never raises — because connectors degrade, never crash.
"""

from __future__ import annotations

from enum import StrEnum

import httpx

# Cap how much of the raw vendor message we echo into the friendly string.
_DETAIL_MAX = 200

# Statuses worth retrying: rate-limit + upstream 5xx. A 4xx other than 429 is a
# hard client error (bad request, missing repo, bad token) — retrying is futile.
TRANSIENT_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class ErrorCategory(StrEnum):
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    UPSTREAM = "upstream"
    TRANSPORT = "transport"
    UNKNOWN = "unknown"


TRANSIENT_CATEGORIES: frozenset[ErrorCategory] = frozenset(
    {ErrorCategory.RATE_LIMIT, ErrorCategory.UPSTREAM, ErrorCategory.TRANSPORT}
)

_FRIENDLY: dict[ErrorCategory, str] = {
    ErrorCategory.AUTH: (
        "Authentication failed — check the connector's API token/credentials."
    ),
    ErrorCategory.RATE_LIMIT: (
        "Rate limit reached for the connector's API. Wait and retry."
    ),
    ErrorCategory.NOT_FOUND: (
        "Resource not found — check the connector's owner/repo/project config."
    ),
    ErrorCategory.UPSTREAM: (
        "The vendor API returned a temporary server error. Usually transient."
    ),
    ErrorCategory.TRANSPORT: (
        "Could not reach the vendor API (network/connection error)."
    ),
    ErrorCategory.UNKNOWN: "The connector call failed.",
}


class ConnectorError(RuntimeError):
    """A classified connector failure carrying a friendly message + routing flags."""

    def __init__(self, message: str, *, category: str, transient: bool):
        super().__init__(message)
        self.category = category
        self.transient = transient


def is_transient_status(status: int) -> bool:
    """Whether an HTTP status is worth retrying."""
    return status in TRANSIENT_STATUSES


def _status_code(exc: BaseException) -> int | None:
    """Best-effort HTTP status from an httpx (or httpx-shaped) exception."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    return code if isinstance(code, int) else None


def classify_category(exc: BaseException) -> ErrorCategory:
    """Map any exception to an ``ErrorCategory``."""
    if isinstance(exc, httpx.TransportError):
        return ErrorCategory.TRANSPORT
    status = _status_code(exc)
    if status == 429:
        return ErrorCategory.RATE_LIMIT
    if status in (401, 403):
        return ErrorCategory.AUTH
    if status == 404:
        return ErrorCategory.NOT_FOUND
    if isinstance(status, int) and 500 <= status < 600:
        return ErrorCategory.UPSTREAM
    return ErrorCategory.UNKNOWN


def _detail(exc: BaseException) -> str:
    raw = str(exc).strip().splitlines()
    return (raw[0] if raw else "")[:_DETAIL_MAX]


def classify_connector_error(exc: BaseException) -> ConnectorError:
    """Wrap ``exc`` in a ``ConnectorError`` with a friendly message + flags."""
    category = classify_category(exc)
    base = _FRIENDLY[category]
    detail = _detail(exc)
    message = f"{base} ({detail})" if detail else base
    return ConnectorError(
        message,
        category=category.value,
        transient=category in TRANSIENT_CATEGORIES,
    )
