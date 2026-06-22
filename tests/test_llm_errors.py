"""Tests for the provider-agnostic error classifier."""

import pytest

from productagents.llm_errors import (
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
