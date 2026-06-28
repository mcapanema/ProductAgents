"""Tests for the dev WebSocket bridge — same dispatch as ipc, different transport."""

import json

from productagents.app import devbridge


class _FakeWS:
    """Stand-in for a websockets connection: replays messages, records sends."""

    def __init__(self, messages):
        self._messages = list(messages)
        self.sent: list[str] = []

    async def send(self, data: str) -> None:
        self.sent.append(data)

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for message in self._messages:
            yield message


class _FakeSessions:
    async def list(self):
        return []


def _services():
    return {
        "workflows": None,
        "workspaces": None,
        "active_name": "default",
        "sessions": _FakeSessions(),
        "decisions": None,
    }


async def test_connection_dispatches_each_message_via_handle():
    ws = _FakeWS([json.dumps({"id": 1, "method": "sessions.list"})])
    await devbridge._handle_connection(ws, services=_services())
    assert json.loads(ws.sent[0]) == {"id": 1, "result": []}


async def test_invalid_json_emits_error_and_keeps_serving():
    ws = _FakeWS(["not json", json.dumps({"id": 2, "method": "sessions.list"})])
    await devbridge._handle_connection(ws, services=_services())
    msgs = [json.loads(s) for s in ws.sent]
    assert msgs[0]["id"] is None
    assert "invalid json" in msgs[0]["error"]
    assert msgs[1]["id"] == 2  # loop continued after the bad message


async def test_blank_message_is_skipped():
    ws = _FakeWS(["   ", json.dumps({"id": 3, "method": "sessions.list"})])
    await devbridge._handle_connection(ws, services=_services())
    assert [json.loads(s)["id"] for s in ws.sent] == [3]
