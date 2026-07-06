"""The Obsidian note → CustomerFeedback mapper (pure)."""

from datetime import UTC, datetime

from productagents.connectors.obsidian.mappers import (
    extract_tags,
    note_to_feedback,
    split_note,
)
from tests.canonical_harness import assert_no_vendor_leakage

_MTIME = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)
_TEXT = "---\ntags: [customer, churn]\n---\nUser says export is too slow. #feedback"


def test_maps_core_fields(tmp_path):
    path = tmp_path / "interviews" / "Churn interview.md"
    fb = note_to_feedback(path, tmp_path, _TEXT, _MTIME)
    assert fb.body == "Churn interview\n\nUser says export is too slow. #feedback"
    assert fb.author is None
    assert fb.submitted_at == _MTIME
    assert fb.tags == ["customer", "churn", "feedback"]
    assert fb.sentiment is None
    assert fb.segment is None


def test_lineage_carries_vendor_identity(tmp_path):
    path = tmp_path / "interviews" / "Churn interview.md"
    fb = note_to_feedback(path, tmp_path, _TEXT, _MTIME)
    assert fb.source.connector == "obsidian"
    assert fb.source.vendor_type == "note"
    assert fb.source.vendor_id == "interviews/Churn interview.md"
    assert fb.source.url == path.as_uri()
    assert fb.raw_fingerprint is not None


def test_note_without_frontmatter(tmp_path):
    fb = note_to_feedback(tmp_path / "Idea.md", tmp_path, "plain body", _MTIME)
    assert fb.body == "Idea\n\nplain body"
    assert fb.tags == []


def test_split_note():
    assert split_note("plain body") == ("", "plain body")
    assert split_note("---\ntags: a\n---\nbody") == ("tags: a", "body")


def test_extract_tags_dedupes_and_handles_flat_forms():
    assert extract_tags("tags: [a, b]", "body #a #c") == ["a", "b", "c"]
    assert extract_tags("tags: a, b", "") == ["a", "b"]
    assert extract_tags("", "no tags here") == []


def test_no_vendor_terms_leak_into_domain_fields(tmp_path):
    fb = note_to_feedback(tmp_path / "Churn interview.md", tmp_path, _TEXT, _MTIME)
    assert_no_vendor_leakage(fb, banned_terms=["obsidian", "vault"])
