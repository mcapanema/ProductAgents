"""Tests for the `config.*` IPC methods."""

from productagents.app import ipc
from tests._ipc_helpers import _collect, _FakeSessions, _workflows
from tests.fakes import ready_status


class _FakeConfigService:
    """Stand-in for ConfigurationService: canned status + recorded set() calls."""

    def __init__(self, status, providers):
        self._status = status
        self._providers = providers
        self.sets: list[tuple] = []

    def status(self):
        return self._status

    def providers(self):
        return self._providers

    def settings(self):
        return {
            "debate_rounds": 2,
            "judge_threshold": 0.7,
            "judge_max_retries": 1,
            "max_retries": 6,
        }

    def settings_origins(self):
        return dict.fromkeys(
            [
                "model",
                "model_provider",
                "debate_rounds",
                "judge_threshold",
                "judge_max_retries",
                "max_retries",
            ],
            "db",
        )

    async def set(self, model, *, provider=None, api_key=None, settings=None):
        self.sets.append((model, provider, api_key, settings))
        return self._status


def _fake_config():
    from productagents.platform.configuration import PROVIDERS

    return _FakeConfigService(ready_status(), PROVIDERS)


async def test_config_get_returns_status_and_providers():
    config = _fake_config()
    emit, sink = _collect()
    await ipc.handle(
        {"id": 40, "method": "config.get"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "config": config,
        },
        emit=emit,
    )
    result = sink[0]["result"]
    assert result["model"] == "anthropic:claude-sonnet-4-6"
    assert result["provider"] == "anthropic"
    anthropic = next(p for p in result["providers"] if p["id"] == "anthropic")
    assert anthropic["key_var"] == "ANTHROPIC_API_KEY"


async def test_config_set_delegates_to_service():
    config = _fake_config()
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 41,
            "method": "config.set",
            "params": {"model": "openai:gpt-4o", "api_key": "sk-test"},
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "config": config,
        },
        emit=emit,
    )
    assert config.sets == [("openai:gpt-4o", None, "sk-test", None)]
    assert sink[0]["result"]["model"] == "anthropic:claude-sonnet-4-6"


async def test_config_get_includes_settings():
    config = _fake_config()
    emit, sink = _collect()
    await ipc.handle(
        {"id": 44, "method": "config.get"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "config": config,
        },
        emit=emit,
    )
    result = sink[0]["result"]
    settings = result["settings"]
    assert settings["debate_rounds"] == 2
    assert settings["judge_threshold"] == 0.7
    assert settings["judge_max_retries"] == 1
    assert settings["max_retries"] == 6
    assert result["origins"]["model"] == "db"


async def test_config_set_forwards_settings():
    config = _fake_config()
    emit, sink = _collect()
    await ipc.handle(
        {
            "id": 45,
            "method": "config.set",
            "params": {
                "model": "anthropic:m",
                "settings": {"debate_rounds": 3, "log_level": "DEBUG"},
            },
        },
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
            "config": config,
        },
        emit=emit,
    )
    assert config.sets == [
        ("anthropic:m", None, None, {"debate_rounds": 3, "log_level": "DEBUG"})
    ]
    assert sink[0]["result"]["model"] == "anthropic:claude-sonnet-4-6"


async def test_config_method_without_service_errors():
    emit, sink = _collect()
    await ipc.handle(
        {"id": 43, "method": "config.get"},
        {
            "workflows": _workflows(),
            "workspaces": None,
            "active_name": "default",
            "sessions": _FakeSessions(),
        },
        emit=emit,
    )
    assert sink[0]["id"] == 43
    assert "config service not available" in sink[0]["error"]
