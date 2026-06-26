"""Canonical models map to a row and back without losing data."""

from productagents.core.models import CustomerFeedback, Initiative, SourceRef
from productagents.knowledge.repositories.sqlmodel.mapping import from_row, to_row


def test_manual_record_maps_empty_vendor_id_to_none():
    initiative = Initiative(title="Add SSO", description="Enterprise login")
    row = to_row(initiative)
    assert row.pk == str(initiative.id)
    assert row.model_type == "Initiative"
    assert row.connector == "manual"
    assert row.vendor_id is None  # "" collapses to NULL so manual rows don't collide


def test_connector_record_keeps_vendor_id():
    feedback = CustomerFeedback(
        body="Love the new dashboard",
        source=SourceRef(connector="zendesk", vendor_type="ticket", vendor_id="Z-42"),
    )
    row = to_row(feedback)
    assert row.connector == "zendesk"
    assert row.vendor_id == "Z-42"


def test_round_trip_is_byte_stable():
    initiative = Initiative(title="Add SSO", description="Enterprise login")
    restored = from_row(to_row(initiative), Initiative)
    assert restored == initiative


def test_round_trip_preserves_lineage_and_extensions():
    feedback = CustomerFeedback(
        body="x",
        source=SourceRef(connector="zendesk", vendor_type="ticket", vendor_id="Z-1"),
        extensions={"priority_label": "urgent"},
    )
    restored = from_row(to_row(feedback), CustomerFeedback)
    assert restored.source.vendor_id == "Z-1"
    assert restored.extensions == {"priority_label": "urgent"}
