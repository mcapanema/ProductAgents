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


@respx.mock
async def test_retry_after_header_overrides_backoff(monkeypatch):
    """Test that Retry-After header is honored instead of exponential backoff."""
    import productagents.connectors.http as http_mod

    delays: list[float] = []

    async def _record(d: float) -> None:  # capture the sleep instead of really sleeping
        delays.append(d)

    monkeypatch.setattr(http_mod.asyncio, "sleep", _record)

    respx.get("https://api.test/x").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "7"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    async with make_client(base_url="https://api.test") as client:
        resp = await request_with_retry(client, "GET", "/x", base_delay=0.5)

    assert resp.status_code == 200
    assert delays == [7.0]  # honored the header, not base_delay*2**0 == 0.5


@respx.mock
async def test_retry_after_is_capped(monkeypatch):
    """Test that absurdly large Retry-After values are capped."""
    import productagents.connectors.http as http_mod

    delays: list[float] = []

    async def _record(d: float) -> None:
        delays.append(d)

    monkeypatch.setattr(http_mod.asyncio, "sleep", _record)

    respx.get("https://api.test/y").mock(
        side_effect=[
            httpx.Response(503, headers={"Retry-After": "99999"}),
            httpx.Response(200, json={}),
        ]
    )
    async with make_client(base_url="https://api.test") as client:
        await request_with_retry(client, "GET", "/y")

    assert delays == [http_mod._MAX_RETRY_AFTER]
