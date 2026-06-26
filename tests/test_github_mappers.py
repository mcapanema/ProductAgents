"""The GitHub issue → CustomerFeedback mapper (pure)."""

from datetime import UTC, datetime

from productagents.connectors.github.mappers import issue_to_feedback
from tests.canonical_harness import assert_no_vendor_leakage

_ISSUE = {
    "number": 42,
    "title": "Add SSO",
    "body": "We need SAML login",
    "user": {"login": "octocat"},
    "created_at": "2026-01-15T09:30:00Z",
    "updated_at": "2026-01-16T10:00:00Z",
    "labels": [{"name": "enhancement"}, {"name": "auth"}],
    "html_url": "https://github.com/acme/app/issues/42",
}


def test_maps_core_fields():
    fb = issue_to_feedback(_ISSUE)
    assert "Add SSO" in fb.body
    assert "We need SAML login" in fb.body
    assert fb.author == "octocat"
    assert fb.tags == ["enhancement", "auth"]
    assert fb.submitted_at == datetime(2026, 1, 15, 9, 30, tzinfo=UTC)
    assert fb.sentiment is None
    assert fb.segment is None


def test_lineage_carries_vendor_identity():
    fb = issue_to_feedback(_ISSUE)
    assert fb.source.connector == "github"
    assert fb.source.vendor_type == "issue"
    assert fb.source.vendor_id == "42"
    assert fb.source.url == "https://github.com/acme/app/issues/42"
    assert fb.raw_fingerprint is not None


def test_handles_missing_optional_fields():
    minimal = {"number": 7, "title": "Bug", "labels": []}
    fb = issue_to_feedback(minimal)
    assert fb.body.strip() == "Bug"
    assert fb.author is None
    assert fb.submitted_at is None
    assert fb.tags == []
    assert fb.source.vendor_id == "7"


def test_no_vendor_terms_leak_into_domain_fields():
    # The canonical invariant: vendor identity lives on SourceRef, never in the
    # domain payload the agents reason over.
    assert_no_vendor_leakage(
        issue_to_feedback(_ISSUE), banned_terms=["github", "issue"]
    )
