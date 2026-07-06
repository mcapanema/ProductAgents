"""Tests for `productagents config show/set` (persisted workspace config)."""

from types import SimpleNamespace

from productagents.app import cli


class _FakeConfigService:
    def __init__(self, model="anthropic:claude-sonnet-4-6"):
        self._model = model
        self.set_args = None

    def status(self):
        return SimpleNamespace(
            model=self._model,
            provider=None,
            key_var="ANTHROPIC_API_KEY",
            key_present=True,
            problems=[],
        )

    def settings(self):
        return {
            "debate_rounds": 2,
            "judge_threshold": 0.7,
            "judge_max_retries": 1,
            "max_retries": 6,
        }

    def settings_origins(self):
        return {
            "model": "db",
            "model_provider": "default",
            "debate_rounds": "env",
            "judge_threshold": "default",
            "judge_max_retries": "default",
            "max_retries": "default",
        }

    async def set(self, model, *, provider=None, api_key=None, settings=None):
        self.set_args = (model, provider, api_key, settings)
        return self.status()


def test_config_show_prints_status_and_origins(capsys):
    assert cli.config_show(service=_FakeConfigService()) == 0
    out = capsys.readouterr().out
    assert "anthropic:claude-sonnet-4-6" in out
    assert "ANTHROPIC_API_KEY" in out
    assert "debate_rounds: 2  (env)" in out


async def test_config_set_persists_settings(capsys):
    service = _FakeConfigService()
    code = await cli.config_set_cmd(
        None, None, None, ["debate_rounds=3"], service=service
    )
    assert code == 0
    assert service.set_args is not None
    model, _provider, _api_key, settings = service.set_args
    assert model == "anthropic:claude-sonnet-4-6"  # defaults to current
    assert settings == {"debate_rounds": "3"}


async def test_config_set_with_model_and_key(capsys):
    service = _FakeConfigService()
    code = await cli.config_set_cmd(
        "openrouter:deepseek/deepseek-chat-v3-0324:free",
        "openrouter",
        "sk-abc",
        [],
        service=service,
    )
    assert code == 0
    assert service.set_args == (
        "openrouter:deepseek/deepseek-chat-v3-0324:free",
        "openrouter",
        "sk-abc",
        {},
    )


async def test_config_set_rejects_unknown_key(capsys):
    service = _FakeConfigService()
    code = await cli.config_set_cmd(None, None, None, ["bogus=1"], service=service)
    assert code == 1
    assert service.set_args is None
    assert "unknown setting" in capsys.readouterr().out


async def test_config_set_without_model_anywhere_returns_one(capsys):
    service = _FakeConfigService(model=None)
    code = await cli.config_set_cmd(None, None, None, [], service=service)
    assert code == 1
    assert "--model" in capsys.readouterr().out
