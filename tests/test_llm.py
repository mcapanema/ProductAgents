import productagents.llm as llm


def test_default_model_used_when_env_unset(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.delenv("PRODUCTAGENTS_MODEL", raising=False)
    monkeypatch.delenv("PRODUCTAGENTS_MODEL_PROVIDER", raising=False)
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    result = llm.get_model()

    assert result == "MODEL"
    assert captured["model"] == llm.DEFAULT_MODEL
    assert captured["kwargs"] == {}


def test_env_overrides_model_and_provider(monkeypatch):
    captured = {}

    def fake_init(model, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "MODEL"

    monkeypatch.setenv("PRODUCTAGENTS_MODEL", "gpt-5.5")
    monkeypatch.setenv("PRODUCTAGENTS_MODEL_PROVIDER", "openai")
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    llm.get_model()

    assert captured["model"] == "gpt-5.5"
    assert captured["kwargs"] == {"model_provider": "openai"}
