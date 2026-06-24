"""Reusable assertions for canonical-model mappers.

Phase 4 connector mappers (`VendorEntity -> CanonicalModel`) use these to prove
two properties: the canonical model survives a JSON round-trip, and no vendor
concept leaks into the agent-visible *domain* fields. Provenance lives in
`source`/`extensions`/sync metadata, which are exempt by design.
"""

from collections.abc import Iterable

from productagents.core.models import CanonicalModel

# Fields that legitimately carry vendor data and are never read by agents.
_EXEMPT_FIELDS = {
    "id",
    "source",
    "ingested_at",
    "updated_at",
    "raw_fingerprint",
    "extensions",
}


def assert_json_round_trips(model: CanonicalModel) -> None:
    """Assert the model is byte-stable across a JSON dump/load cycle."""
    restored = type(model).model_validate_json(model.model_dump_json())
    assert restored == model, "canonical model did not survive JSON round-trip"


def assert_no_vendor_leakage(
    model: CanonicalModel, banned_terms: Iterable[str]
) -> None:
    """Assert no banned vendor term appears in the model's domain fields."""
    domain = model.model_dump(exclude=_EXEMPT_FIELDS, mode="json")
    haystack = str(domain).lower()
    leaked = sorted({t for t in banned_terms if t.lower() in haystack})
    assert not leaked, f"vendor terms leaked into domain fields: {leaked}"
