from productagents.agents.prompts import PromptStore
from productagents.app import cli
from productagents.platform.prompt_service import PromptService


def _service(tmp_path):
    return PromptService(PromptStore(tmp_path))


def test_prompts_list_prints_names(tmp_path, capsys):
    code = cli.prompts_list(service=_service(tmp_path))
    out = capsys.readouterr().out
    assert code == 0
    assert "market" in out


def test_prompts_show_active(tmp_path, capsys):
    service = _service(tmp_path)
    service.save("market", "EDITED BODY")
    code = cli.prompts_show("market", None, service=service)
    assert code == 0
    assert "EDITED BODY" in capsys.readouterr().out


def test_prompts_show_unknown_returns_1(tmp_path, capsys):
    code = cli.prompts_show("nope", None, service=_service(tmp_path))
    assert code == 1
    assert "no such prompt" in capsys.readouterr().out


def test_prompts_save_from_file(tmp_path, capsys):
    service = _service(tmp_path)
    body = tmp_path / "new.txt"
    body.write_text("FROM FILE $evidence", encoding="utf-8")
    code = cli.prompts_save("market", str(body), service=service)
    assert code == 0
    assert service.get("market") == "FROM FILE $evidence"
    assert "saved market v1" in capsys.readouterr().out


def test_prompts_rollback(tmp_path, capsys):
    service = _service(tmp_path)
    service.save("market", "one")
    service.save("market", "two")
    code = cli.prompts_rollback("market", 1, service=service)
    assert code == 0
    assert service.get("market") == "one"


def test_prompts_rollback_unknown_version_returns_1(tmp_path, capsys):
    service = PromptService(PromptStore(tmp_path))
    code = cli.prompts_rollback("market", 99, service=service)
    assert code == 1
    assert "no version 99 for market" in capsys.readouterr().out


def test_prompts_diff(tmp_path, capsys):
    service = _service(tmp_path)
    service.save("market", "a\n")
    service.save("market", "b\n")
    code = cli.prompts_diff("market", 1, 2, service=service)
    assert code == 0
    out = capsys.readouterr().out
    assert "-a" in out
    assert "+b" in out


def test_prompts_save_invalid_template_returns_1(tmp_path, capsys):
    service = _service(tmp_path)
    body = tmp_path / "bad.txt"
    body.write_text("uses $nonsense", encoding="utf-8")
    code = cli.prompts_save("market", str(body), service=service)
    assert code == 1
    out = capsys.readouterr().out
    assert "$nonsense" in out
    # nothing was written
    assert service.versions("market") == [0]
