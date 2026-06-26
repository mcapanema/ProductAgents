"""The single generic table that backs every canonical entity."""

from datetime import datetime

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


class CanonicalRecord(SQLModel, table=True):
    """One row per synced/created canonical entity.

    Lineage and sync fields are real columns (indexed, used for dedup and
    incremental sync); the full domain payload is stored verbatim as JSON so the
    canonical model round-trips byte-for-byte.
    """

    __tablename__ = "canonical_record"
    __table_args__ = (
        UniqueConstraint(
            "connector", "vendor_type", "vendor_id", name="uq_canonical_source"
        ),
    )

    pk: str = Field(primary_key=True)  # CanonicalModel.id
    model_type: str = Field(index=True)  # e.g. "Initiative", "CustomerFeedback"
    connector: str
    vendor_type: str
    vendor_id: str | None = Field(default=None, index=True)  # None for manual records
    raw_fingerprint: str | None = Field(default=None)
    ingested_at: datetime
    updated_at: datetime
    payload: dict = Field(sa_column=Column(JSON))  # model_dump(mode="json")
