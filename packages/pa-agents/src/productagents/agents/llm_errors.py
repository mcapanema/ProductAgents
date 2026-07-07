"""Provider-agnostic classification of LLM call failures.

This module deliberately imports no provider SDK. It inspects an arbitrary
exception by three generic signals — an HTTP status code (if the SDK attached
one), the exception's class name, and its message text — and maps it to a small
set of actionable categories. That keeps the mapping working across providers
(OpenRouter, Anthropic, OpenAI, …) without coupling to any one client's types.

A `fatal` category is one where retrying *every* node is pointless because the
condition is systemic for the whole run (bad key, exhausted rate limit, a model
that cannot do tool calling). The caller uses `fatal` to fail the run fast
instead of degrading node after node.
"""

from __future__ import annotations

from enum import StrEnum

# Cap how much of the provider's raw message we echo into the friendly string.
_DETAIL_MAX = 200


class ErrorCategory(StrEnum):
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    TOOL_CALLING_UNSUPPORTED = "tool_calling_unsupported"
    UPSTREAM = "upstream"
    UNKNOWN = "unknown"


FATAL_CATEGORIES: frozenset[ErrorCategory] = frozenset(
    {
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.AUTH,
        ErrorCategory.TOOL_CALLING_UNSUPPORTED,
    }
)

_FRIENDLY: dict[ErrorCategory, str] = {
    ErrorCategory.RATE_LIMIT: (
        "Rate limit reached for the configured model. Wait and retry, switch to "
        "another model, or add provider credits."
    ),
    ErrorCategory.AUTH: (
        "Authentication failed for the model provider. Check that the matching "
        "API key is set and valid."
    ),
    ErrorCategory.TOOL_CALLING_UNSUPPORTED: (
        "The configured model does not support tool/function calling, which "
        "structured output requires. Choose a tool-capable model."
    ),
    ErrorCategory.UPSTREAM: (
        "The model provider returned a temporary upstream error. This is usually "
        "transient — retry in a moment or switch models."
    ),
    ErrorCategory.UNKNOWN: "The model provider call failed.",
}


class ProviderError(RuntimeError):
    """A classified LLM call failure carrying a friendly message and routing flags."""

    def __init__(self, message: str, *, category: str, fatal: bool):
        super().__init__(message)
        self.category = category
        self.fatal = fatal


class StructuredOutputError(ProviderError):
    """Raised when a structured-output call returns no parsed object.

    A `None` result almost always means the configured model does not support
    tool/function calling, which `with_structured_output` requires. Always fatal:
    if one node gets `None`, every node will.
    """

    def __init__(self, message: str):
        super().__init__(
            message,
            category=ErrorCategory.TOOL_CALLING_UNSUPPORTED.value,
            fatal=True,
        )


def _status_code(exc: BaseException) -> int | None:
    """Best-effort extraction of an HTTP status code from a provider exception."""
    for attr in ("status_code", "http_status", "status", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    return code if isinstance(code, int) else None


def classify_category(exc: BaseException) -> ErrorCategory:
    """Map any exception to an `ErrorCategory`.

    When the SDK attached an HTTP status code it is authoritative: decide by
    status first, so a transient 5xx whose body happens to mention "api key" is
    not misread as a fatal auth failure. Only when there is no status (or one we
    don't special-case, e.g. 400/404) do we fall back to sniffing the class name
    and message text.
    """
    status = _status_code(exc)
    if status is not None:
        if status == 429:
            return ErrorCategory.RATE_LIMIT
        if status in (401, 403):
            return ErrorCategory.AUTH
        if 500 <= status < 600:
            return ErrorCategory.UPSTREAM

    name = type(exc).__name__.lower()
    text = str(exc).lower()

    if (
        "ratelimit" in name
        or "toomanyrequests" in name
        or "rate limit" in text
        or "quota" in text
        or "free-models-per-day" in text
    ):
        return ErrorCategory.RATE_LIMIT

    if (
        any(
            k in name
            for k in (
                "authentication",
                "unauthorized",
                "permissiondenied",
                "invalidapikey",
            )
        )
        or "api key" in text
        or "unauthorized" in text
    ):
        return ErrorCategory.AUTH

    if (
        any(
            k in name
            for k in (
                "internalserver",
                "serviceunavailable",
                "badgateway",
                "responsevalidation",
                "apiconnection",
                "apitimeout",
            )
        )
        or "internal server error" in text
        or "502" in text
        or "503" in text
    ):
        return ErrorCategory.UPSTREAM

    return ErrorCategory.UNKNOWN


def _detail(exc: BaseException) -> str:
    """First line of the provider message, trimmed — preserves useful guidance."""
    raw = str(exc).strip().splitlines()
    first = raw[0] if raw else ""
    return first[:_DETAIL_MAX]


def classify_provider_error(exc: BaseException) -> ProviderError:
    """Wrap `exc` in a `ProviderError` with a friendly message and `fatal` flag."""
    category = classify_category(exc)
    base = _FRIENDLY[category]
    detail = _detail(exc)
    message = f"{base} (provider said: {detail})" if detail else base
    return ProviderError(
        message, category=category.value, fatal=category in FATAL_CATEGORIES
    )
