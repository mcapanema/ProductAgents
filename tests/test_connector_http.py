"""The shared httpx client factory + transient-retry helper."""

import httpx
import pytest
import respx

from productagents.connectors.http import make_client, request_with_retry


def test_make_client_sets_auth_and_headers():
    client = make_client(
        base_url="https://api.example.com",
        token="secret",
        headers={"Accept": "application/json"},
    )
    assert client.headers["authorization"] == "Bearer secret"
    assert client.headers["accept"] == "application/json"
    assert str(client.base_url) == "https://api.example.com"


def test_make_client_without_token_has_no_auth_header():
    client = make_client(base_url="https://api.example.com")
    assert "authorization" not in client.headers


@respx.mock
async def test_retry_recovers_after_transient_status():
    route = respx.get("https://api.example.com/x").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": True})]
    )
    async with make_client(base_url="https://api.example.com") as client:
        resp = await request_with_retry(
            client, "GET", "/x", max_retries=3, base_delay=0
        )
    assert resp.status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_retry_gives_up_and_raises_after_budget():
    respx.get("https://api.example.com/x").mock(
        side_effect=[httpx.Response(503), httpx.Response(503), httpx.Response(503)]
    )
    async with make_client(base_url="https://api.example.com") as client:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await request_with_retry(client, "GET", "/x", max_retries=2, base_delay=0)
        assert exc_info.value.response.status_code == 503


@respx.mock
async def test_non_transient_4xx_raises_immediately():
    route = respx.get("https://api.example.com/x").mock(
        return_value=httpx.Response(404)
    )
    async with make_client(base_url="https://api.example.com") as client:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await request_with_retry(client, "GET", "/x", max_retries=3, base_delay=0)
        assert exc_info.value.response.status_code == 404
    assert route.call_count == 1  # no retry on a hard client error


@respx.mock
async def test_retry_exhausts_budget_on_transport_error():
    respx.get("https://api.example.com/x").mock(
        side_effect=httpx.ConnectError("connection failed")
    )
    async with make_client(base_url="https://api.example.com") as client:
        with pytest.raises(httpx.ConnectError):
            await request_with_retry(client, "GET", "/x", max_retries=2, base_delay=0)


@respx.mock
async def test_retry_logs_a_warning_per_transient_attempt(caplog):
    import logging

    with respx.mock:
        respx.get("https://api.example.com/x").mock(
            side_effect=[httpx.Response(503), httpx.Response(200, json={})]
        )
        with caplog.at_level(logging.WARNING, logger="productagents.connectors"):
            async with make_client(base_url="https://api.example.com") as client:
                await request_with_retry(
                    client, "GET", "/x", max_retries=3, base_delay=0
                )
    assert any("retry" in r.getMessage() for r in caplog.records)
