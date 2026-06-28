from productagents.platform.prompt_service import PromptService


def test_create_reads_prompts_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PRODUCTAGENTS_PROMPTS_DIR", str(tmp_path))
    service = PromptService.create()
    assert "market" in service.names()


def test_save_read_rollback_roundtrip(tmp_path):
    from productagents.agents.prompts import PromptStore

    service = PromptService(PromptStore(tmp_path))
    assert service.versions("market") == [0]
    v1 = service.save("market", "edited one")
    v2 = service.save("market", "edited two")
    assert (v1, v2) == (1, 2)
    assert service.get("market") == "edited two"
    v3 = service.rollback("market", 1)
    assert v3 == 3
    assert service.read("market", 3) == "edited one"


def test_diff_between_versions(tmp_path):
    from productagents.agents.prompts import PromptStore

    service = PromptService(PromptStore(tmp_path))
    service.save("market", "alpha\n")
    service.save("market", "beta\n")
    d = service.diff("market", 1, 2)
    assert "-alpha" in d
    assert "+beta" in d
