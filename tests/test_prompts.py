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


def test_save_version_creates_v1_and_becomes_active(tmp_path):
    store = PromptStore(tmp_path)
    v = store.save_version("market", "OVERRIDDEN $evidence")
    assert v == 1
    assert store.active_version("market") == 1
    assert store.get("market") == "OVERRIDDEN $evidence"
    assert store.render("market", evidence="X") == "OVERRIDDEN X"


def test_versions_lists_zero_then_overrides(tmp_path):
    store = PromptStore(tmp_path)
    store.save_version("market", "a")
    store.save_version("market", "b")
    assert store.versions("market") == [0, 1, 2]


def test_read_version_zero_is_the_bundled_default(tmp_path):
    store = PromptStore(tmp_path)
    store.save_version("market", "override")
    assert "Market Analyst" in store.read_version("market", 0)
    assert store.read_version("market", 1) == "override"


def test_rollback_reappends_old_text_as_new_active_version(tmp_path):
    store = PromptStore(tmp_path)
    store.save_version("market", "v1-text")
    store.save_version("market", "v2-text")
    new = store.rollback("market", 1)
    assert new == 3
    assert store.active_version("market") == 3
    assert store.get("market") == "v1-text"


def test_diff_is_a_unified_diff(tmp_path):
    store = PromptStore(tmp_path)
    store.save_version("market", "line one\n")
    store.save_version("market", "line two\n")
    d = store.diff("market", 1, 2)
    assert "-line one" in d
    assert "+line two" in d


def test_names_unions_bundled_and_overrides(tmp_path):
    store = PromptStore(tmp_path)
    store.save_version("my_custom_prompt", "hi")
    names = store.names()
    assert "market" in names  # bundled
    assert "my_custom_prompt" in names  # override-only
    assert names == sorted(names)


def test_bundled_only_store_has_no_override_versions():
    # no prompts_dir → only version 0 exists
    assert PromptStore().versions("market") == [0]
    assert PromptStore().active_version("market") == 0


# ---------------------------------------------------------------------------
# Task 3: all 13 bundled prompts render without leftover placeholders
# ---------------------------------------------------------------------------

_PROMPT_SLOTS = {
    "market": {"initiative": "i", "evidence": "e"},
    "customer_research": {"initiative": "i", "evidence": "e"},
    "product_analytics": {"initiative": "i", "evidence": "e"},
    "business": {"initiative": "i", "evidence": "e"},
    "technical": {"initiative": "i", "evidence": "e"},
    "debate": {"persona": "p", "initiative": "i", "reports": "r", "history": "h"},
    "debate.advocate": {},
    "debate.skeptic": {},
    "strategist": {
        "initiative": "i",
        "reports": "r",
        "debate": "d",
        "lessons": "l",
        "critique": "c",
    },
    "judge": {
        "initiative": "i",
        "recommendation": "rec",
        "reports": "r",
        "debate": "d",
    },
    "risk": {
        "role": "ro",
        "focus": "f",
        "initiative": "i",
        "recommendation": "rec",
        "reports": "r",
        "debate": "d",
    },
    "governance": {
        "initiative": "i",
        "recommendation": "rec",
        "risks": "rk",
        "portfolio": "p",
    },
    "reflection": {
        "initiative": "i",
        "recommendation": "rec",
        "confidence": "0.5",
        "expected_outcomes": "eo",
        "outcome_note": "on",
    },
}


@pytest.mark.parametrize(("name", "slots"), _PROMPT_SLOTS.items())
def test_every_bundled_prompt_renders_with_no_leftover_placeholder(name, slots):
    out = PromptStore().render(name, **slots)
    assert "$" not in out  # every $slot was filled and no stray $ remains


def test_registry_lists_all_thirteen_bundled_prompts():
    assert set(_PROMPT_SLOTS) <= set(PromptStore().names())


def test_override_versions_ignores_non_numeric_stems(tmp_path):
    store = PromptStore(tmp_path)
    store.save_version("market", "real-v1")
    # a hand-placed malformed file must not crash version listing
    (tmp_path / "market" / "1note.txt").write_text("junk", encoding="utf-8")
    assert store.versions("market") == [0, 1]
    assert store.active_version("market") == 1


# ---------------------------------------------------------------------------
# Phase 5 (H3): save-time template validation
# ---------------------------------------------------------------------------


def test_save_version_rejects_unknown_placeholder(tmp_path):
    store = PromptStore(tmp_path)
    # market's bundled default only offers $initiative and $evidence
    with pytest.raises(ValueError, match=r"\$typo"):
        store.save_version("market", "OVERRIDDEN $typo")
    # nothing was written — active version stays at the bundled default
    assert store.active_version("market") == 0


def test_save_version_rejects_bare_dollar_sign(tmp_path):
    store = PromptStore(tmp_path)
    # a literal "$5" is an invalid placeholder; $$ is the escape
    with pytest.raises(ValueError, match=r"\$\$"):
        store.save_version("market", "costs $5 for $evidence")
    assert store.active_version("market") == 0


def test_save_version_accepts_a_subset_of_known_placeholders(tmp_path):
    store = PromptStore(tmp_path)
    v = store.save_version("market", "just $initiative, no evidence")
    assert v == 1
    assert store.get("market") == "just $initiative, no evidence"


def test_save_version_accepts_escaped_dollar(tmp_path):
    store = PromptStore(tmp_path)
    v = store.save_version("market", "price is $$5 for $evidence")
    assert v == 1
    # $$ collapses to a single literal $ at render, $evidence is substituted
    assert store.render("market", initiative="i", evidence="e") == "price is $5 for e"


def test_save_version_skips_identifier_check_for_custom_prompt(tmp_path):
    # a name with no bundled default has no reference set — only syntax is enforced
    store = PromptStore(tmp_path)
    v = store.save_version("my_custom_prompt", "anything with $whatever")
    assert v == 1
    with pytest.raises(ValueError, match=r"invalid \$placeholder"):
        store.save_version("my_custom_prompt", "bad $")
