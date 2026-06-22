import logging

import productagents.llm as llm


def test_default_model_used_when_env_unset(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.delenv("PRODUCTAGENTS_MODEL", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MAX_RETRIES", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    result = llm.get_model()

    assert result == "MODEL"
    assert captured["model"] == llm.DEFAULT_MODEL
    assert captured["kwargs"] == {"max_retries": 6}


def test_env_overrides_model_and_provider(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.setenv("PRODUCTAGENTS_MODEL", "gpt-5.5")
    monkeypatch.setenv("PRODUCTAGENTS_MODEL_PROVIDER", "openai")
    monkeypatch.delenv("PRODUCTAGENTS_MAX_RETRIES", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["model"] == "gpt-5.5"
    assert captured["kwargs"] == {"model_provider": "openai", "max_retries": 6}


def test_default_max_retries_passed(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.delenv("PRODUCTAGENTS_MODEL", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MAX_RETRIES", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["kwargs"]["max_retries"] == 6


def test_max_retries_env_override(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.delenv("PRODUCTAGENTS_MODEL", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.setenv("PRODUCTAGENTS_MAX_RETRIES", "10")
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["kwargs"]["max_retries"] == 10


def test_max_retries_passed_with_provider(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.setenv("PRODUCTAGENTS_MODEL", "gpt-5.5")
    monkeypatch.setenv("PRODUCTAGENTS_MODEL_PROVIDER", "openai")
    monkeypatch.delenv("PRODUCTAGENTS_MAX_RETRIES", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["kwargs"]["model_provider"] == "openai"
    assert captured["kwargs"]["max_retries"] == 6


def test_openrouter_free_model_resolves_to_chatopenrouter(monkeypatch):
    """An `openrouter:…:free` id resolves to a real ChatOpenRouter.

    This exercises the real `init_chat_model` (no monkeypatching of it), so it
    proves both that `langchain-openrouter` is installed and that the provider
    prefix is split off while the `:free` suffix is preserved. Constructing the
    model makes no network call; the dummy key is never used.
    """
    monkeypatch.setenv(
        "PRODUCTAGENTS_MODEL", "openrouter:deepseek/deepseek-chat-v3-0324:free"
    )
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-a-real-key")

    model = llm.get_model()

    assert type(model).__name__ == "ChatOpenRouter"
    # init_chat_model strips the `openrouter:` provider prefix (first colon only)
    # and keeps the rest verbatim — including the `:free` suffix.
    assert model.model == "deepseek/deepseek-chat-v3-0324:free"


def test_get_model_logs_resolved_model(monkeypatch, caplog):
    monkeypatch.setenv("PRODUCTAGENTS_MODEL", "anthropic:claude-sonnet-4-6")
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MAX_RETRIES", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", lambda model, **kwargs: "MODEL")

    with caplog.at_level(logging.INFO, logger="productagents.llm"):
        llm.get_model()

    assert any("anthropic:claude-sonnet-4-6" in r.getMessage() for r in caplog.records)
