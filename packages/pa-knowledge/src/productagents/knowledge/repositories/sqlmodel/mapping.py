"""Pure mapping between canonical models and their stored row.

The row mirrors lineage/sync fields into real columns (for dedup, indexing, and
incremental sync) while storing the *full* canonical dump as JSON. Storing the
whole dump — not a field-split — is what makes the round-trip exact.
"""

from productagents.core.models import CanonicalModel
from productagents.knowledge.repositories.sqlmodel.tables import CanonicalRecord


def to_row(model: CanonicalModel) -> CanonicalRecord:
    """Project a canonical model onto its storage row."""
    return CanonicalRecord(
        pk=str(model.id),
        model_type=type(model).__name__,
        connector=model.source.connector,
        vendor_type=model.source.vendor_type,
        vendor_id=model.source.vendor_id or None,
        raw_fingerprint=model.raw_fingerprint,
        ingested_at=model.ingested_at,
        updated_at=model.updated_at,
        payload=model.model_dump(mode="json"),
    )


def from_row[T: CanonicalModel](row: CanonicalRecord, model_type: type[T]) -> T:
    """Rebuild a canonical model of ``model_type`` from a stored row."""
    return model_type.model_validate(row.payload)
