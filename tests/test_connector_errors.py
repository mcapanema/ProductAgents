"""Provider-agnostic classification of connector (HTTP) failures."""

import httpx

from productagents.connectors.connector_errors import (
    ConnectorError,
    ErrorCategory,
    classify_category,
    classify_connector_error,
    is_transient_status,
)


def _status_error(code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.example.com/x")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


def test_transient_statuses():
    assert is_transient_status(429)
    assert is_transient_status(503)
    assert not is_transient_status(404)
    assert not is_transient_status(200)


def test_classify_status_codes():
    assert classify_category(_status_error(401)) is ErrorCategory.AUTH
    assert classify_category(_status_error(403)) is ErrorCategory.AUTH
    assert classify_category(_status_error(429)) is ErrorCategory.RATE_LIMIT
    assert classify_category(_status_error(404)) is ErrorCategory.NOT_FOUND
    assert classify_category(_status_error(503)) is ErrorCategory.UPSTREAM


def test_classify_transport_error():
    assert classify_category(httpx.ConnectError("nope")) is ErrorCategory.TRANSPORT


def test_classify_unknown():
    assert classify_category(ValueError("weird")) is ErrorCategory.UNKNOWN


def test_classify_connector_error_carries_flags_and_friendly_message():
    info = classify_connector_error(_status_error(401))
    assert isinstance(info, ConnectorError)
    assert info.category == "auth"
    assert info.transient is False
    assert "Authentication failed" in str(info)


def test_rate_limit_is_transient():
    info = classify_connector_error(_status_error(429))
    assert info.transient is True
