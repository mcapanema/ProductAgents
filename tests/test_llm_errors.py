"""Tests for the provider-agnostic error classifier."""

import pytest

from productagents.agents.llm_errors import (
    ErrorCategory,
    ProviderError,
    StructuredOutputError,
    classify_category,
    classify_provider_error,
)


class _StatusExc(Exception):
    """Stand-in for a provider SDK error that carries an HTTP status code."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


class TooManyRequestsResponseError(Exception):
    """Name mirrors OpenRouter's real class; classification keys off the name."""


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (
            TooManyRequestsResponseError("Rate limit exceeded: free-models-per-day"),
            ErrorCategory.RATE_LIMIT,
        ),
        (_StatusExc("slow down", 429), ErrorCategory.RATE_LIMIT),
        (RuntimeError("You exceeded your quota"), ErrorCategory.RATE_LIMIT),
        (_StatusExc("nope", 401), ErrorCategory.AUTH),
        (RuntimeError("Invalid API key provided"), ErrorCategory.AUTH),
        (_StatusExc("upstream", 502), ErrorCategory.UPSTREAM),
        (RuntimeError("Provider returned error"), ErrorCategory.UNKNOWN),
    ],
)
def test_classify_category(exc, expected):
    assert classify_category(exc) is expected


def test_classify_provider_error_sets_fatal_and_friendly_message():
    err = classify_provider_error(
        RuntimeError("Rate limit exceeded: free-models-per-day. Add 10 credits")
    )
    assert isinstance(err, ProviderError)
    assert err.category == ErrorCategory.RATE_LIMIT.value
    assert err.fatal is True
    # Friendly guidance present, plus the provider's own detail preserved.
    assert "rate limit" in str(err).lower()
    assert "Add 10 credits" in str(err)


def test_upstream_is_not_fatal():
    err = classify_provider_error(RuntimeError("Internal server error 503"))
    assert err.category == ErrorCategory.UPSTREAM.value
    assert err.fatal is False


def test_structured_output_error_is_fatal_tool_calling():
    err = StructuredOutputError(
        "model returned no structured output; tool/function calling"
    )
    assert isinstance(err, ProviderError)
    assert err.category == ErrorCategory.TOOL_CALLING_UNSUPPORTED.value
    assert err.fatal is True
    assert "tool/function calling" in str(err)


def test_status_429_outranks_auth_text():
    """Status 429 should override auth-like text patterns."""
    # Message contains "unauthorized" keyword but status says rate limit.
    exc = _StatusExc("429: Your session is unauthorized to use the API", 429)
    assert classify_category(exc) is ErrorCategory.RATE_LIMIT


def test_status_5xx_outranks_api_key_text():
    # A transient upstream error whose body mentions an API key must classify as
    # UPSTREAM (transient), not AUTH (fatal) — status wins over text.
    exc = _StatusExc("upstream failure: check your api key later", 503)
    assert classify_category(exc) is ErrorCategory.UPSTREAM


def test_burst_429_is_not_fatal():
    # A plain burst 429 (no quota/credit text) is transient — the client's
    # retry budget should absorb it, so it must NOT abort the run.
    err = classify_provider_error(_StatusExc("Too many requests, slow down", 429))
    assert err.category == ErrorCategory.RATE_LIMIT.value
    assert err.fatal is False


def test_quota_429_is_fatal():
    err = classify_provider_error(RuntimeError("You exceeded your monthly quota"))
    assert err.category == ErrorCategory.RATE_LIMIT.value
    assert err.fatal is True


def test_auth_is_fatal():
    err = classify_provider_error(_StatusExc("nope", 401))
    assert err.category == ErrorCategory.AUTH.value
    assert err.fatal is True


def test_unknown_is_not_fatal():
    err = classify_provider_error(RuntimeError("Provider returned error"))
    assert err.category == ErrorCategory.UNKNOWN.value
    assert err.fatal is False
