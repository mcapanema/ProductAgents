import pytest

from productagents.agents.prompts import PromptStore


def test_bundled_get_returns_raw_default_template():
    store = PromptStore()
    text = store.get("market")
    assert "Market Analyst" in text
    assert "$evidence" in text  # raw template still holds the placeholder


def test_render_substitutes_named_slots():
    out = PromptStore().render("market", initiative="THE-INIT", evidence="THE-DATA")
    assert "THE-INIT" in out
    assert "THE-DATA" in out
    assert "$evidence" not in out
    assert "$initiative" not in out


def test_render_inserts_untrusted_data_literally():
    # data containing braces and dollars must NOT be re-parsed
    out = PromptStore().render("market", initiative="{x}", evidence="cost is $5 {note}")
    assert "cost is $5 {note}" in out
    assert "{x}" in out


def test_unknown_prompt_raises_keyerror():
    with pytest.raises(KeyError):
        PromptStore().get("does-not-exist")
