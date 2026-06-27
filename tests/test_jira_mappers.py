"""The Jira issue → CustomerFeedback mapper (pure)."""

from datetime import UTC, datetime

from productagents.connectors.jira.mappers import adf_to_text, issue_to_feedback
from tests.canonical_harness import assert_no_vendor_leakage

_ISSUE = {
    "key": "PROJ-42",
    "fields": {
        "summary": "Add SSO",
        "description": {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "We need SAML login"}],
                }
            ],
        },
        "reporter": {"displayName": "Jane Reporter"},
        "created": "2026-01-15T09:30:00.000+0000",
        "updated": "2026-01-16T10:00:00.000+0000",
        "labels": ["enhancement", "auth"],
    },
}

_SITE = "https://acme.atlassian.net"


def test_maps_core_fields():
    fb = issue_to_feedback(_ISSUE, base_url=_SITE)
    assert "Add SSO" in fb.body
    assert "We need SAML login" in fb.body
    assert fb.author == "Jane Reporter"
    assert fb.tags == ["enhancement", "auth"]
    assert fb.submitted_at == datetime(2026, 1, 15, 9, 30, tzinfo=UTC)
    assert fb.sentiment is None
    assert fb.segment is None


def test_lineage_carries_vendor_identity():
    fb = issue_to_feedback(_ISSUE, base_url=_SITE)
    assert fb.source.connector == "jira"
    assert fb.source.vendor_type == "issue"
    assert fb.source.vendor_id == "PROJ-42"
    assert fb.source.url == "https://acme.atlassian.net/browse/PROJ-42"
    assert fb.raw_fingerprint is not None


def test_handles_missing_optional_fields():
    minimal = {"key": "PROJ-7", "fields": {"summary": "Bug", "labels": []}}
    fb = issue_to_feedback(minimal, base_url=_SITE)
    assert fb.body.strip() == "Bug"
    assert fb.author is None
    assert fb.submitted_at is None
    assert fb.tags == []
    assert fb.source.vendor_id == "PROJ-7"


def test_adf_to_text_flattens_nested_text_nodes():
    doc = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Hello "}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "world"}]},
        ],
    }
    assert adf_to_text(doc) == "Hello world"


def test_adf_to_text_empty_for_none_or_plain():
    assert adf_to_text(None) == ""
    assert adf_to_text({"type": "doc", "content": []}) == ""


def test_no_vendor_terms_leak_into_domain_fields():
    assert_no_vendor_leakage(
        issue_to_feedback(_ISSUE, base_url=_SITE), banned_terms=["jira", "issue"]
    )
