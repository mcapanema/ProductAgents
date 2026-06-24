import pytest

from productagents.core.models import CustomerFeedback
from productagents.core.refs import SourceRef
from tests.canonical_harness import assert_json_round_trips, assert_no_vendor_leakage


def _map_vendor_ticket(payload: dict) -> CustomerFeedback:
    """Illustrative pure mapper: a Zendesk-shaped dict -> canonical CustomerFeedback."""
    return CustomerFeedback(
        body=payload["description"],
        sentiment="negative" if payload["satisfaction"] == "bad" else "neutral",
        source=SourceRef(
            connector="zendesk", vendor_type="ticket", vendor_id=str(payload["id"])
        ),
    )


def test_round_trip_helper_accepts_valid_model():
    fb = _map_vendor_ticket({"id": 9, "description": "slow", "satisfaction": "bad"})
    assert_json_round_trips(fb)


def test_no_leakage_passes_when_domain_fields_are_clean():
    fb = _map_vendor_ticket({"id": 9, "description": "slow", "satisfaction": "bad"})
    # "zendesk" lives only in `source`, which is exempt — so this must NOT raise.
    assert_no_vendor_leakage(fb, banned_terms=["zendesk", "satisfaction"])


def test_no_leakage_fails_when_a_vendor_term_reaches_a_domain_field():
    leaky = CustomerFeedback(body="ref zendesk ticket #9", source=SourceRef.manual())
    with pytest.raises(AssertionError):
        assert_no_vendor_leakage(leaky, banned_terms=["zendesk"])
