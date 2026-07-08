"""Tests for the `prompts.*` IPC methods."""

from productagents.app import ipc
from tests._ipc_helpers import _collect, _FakeSessions, _workflows


class _FakePrompts:
    """Stand-in for PromptService backed by an in-memory {name: {version: text}}."""

    def __init__(self, prompts):
        self._prompts = prompts

    def names(self):
        return sorted(self._prompts)

    def versions(self, name):
        return sorted(self._prompts[name])

    def read(self, name, version):
        return self._prompts[name][version]

    def diff(self, name, old, new):
        return f"--- {name}@{old}\n+++ {name}@{new}\n"

    def save(self, name, text):
        versions = self._prompts.setdefault(name, {0: "default"})
        version = max(versions) + 1
        versions[version] = text
        return version

    def rollback(self, name, version):
        return self.save(name, self._prompts[name][version])


async def test_prompts_list_returns_names_versions_and_active():
    prompts = _FakePrompts(
        {"strategist": {0: "default", 1: "v1", 2: "v2"}, "judge": {0: "judge"}}
    )
    emit, sink = _collect()
    await ipc.handle(
        {"id": 30, "method": "prompts.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "prompts": prompts,
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 30,
            "result": [
                {"name": "judge", "versions": [0], "active": 0},
                {"name": "strategist", "versions": [0, 1, 2], "active": 2},
            ],
        }
    ]


async def test_prompts_show_returns_version_text():
    prompts = _FakePrompts({"strategist": {0: "default", 1: "v1", 2: "v2"}})
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 31,
            "method": "prompts.show",
            "params": {"name": "strategist", "version": 2},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "prompts": prompts,
        },
        emit=emit,
    )
    assert sink == [
        {"id": 31, "result": {"name": "strategist", "version": 2, "text": "v2"}}
    ]


async def test_prompts_diff_returns_unified_diff():
    prompts = _FakePrompts({"strategist": {0: "default", 2: "v2"}})
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 32,
            "method": "prompts.diff",
            "params": {"name": "strategist", "old": 0, "new": 2},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "prompts": prompts,
        },
        emit=emit,
    )
    assert sink == [
        {
            "id": 32,
            "result": {
                "name": "strategist",
                "old": 0,
                "new": 2,
                "diff": "--- strategist@0\n+++ strategist@2\n",
            },
        }
    ]


async def test_prompts_method_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 33, "method": "prompts.list"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 33
    assert "prompts service not available" in sink[0]["error"]


async def test_prompts_save_appends_version_and_returns_summary():
    prompts = _FakePrompts({"strategist": {0: "default"}})
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 34,
            "method": "prompts.save",
            "params": {"name": "strategist", "text": "v1 body"},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "prompts": prompts,
        },
        emit=emit,
    )
    assert sink == [
        {"id": 34, "result": {"name": "strategist", "versions": [0, 1], "active": 1}}
    ]


async def test_prompts_rollback_reactivates_and_returns_summary():
    prompts = _FakePrompts({"strategist": {0: "default", 1: "v1"}})
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 35,
            "method": "prompts.rollback",
            "params": {"name": "strategist", "version": 0},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "prompts": prompts,
        },
        emit=emit,
    )
    assert sink == [
        {"id": 35, "result": {"name": "strategist", "versions": [0, 1, 2], "active": 2}}
    ]


async def test_prompts_save_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 36, "method": "prompts.save", "params": {"name": "x", "text": "y"}},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 36
    assert "prompts service not available" in sink[0]["error"]
