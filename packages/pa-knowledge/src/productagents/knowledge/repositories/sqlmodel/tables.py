"""The single generic table that backs every canonical entity."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, TypeDecorator, UniqueConstraint
from sqlmodel import Field, SQLModel


class UTCDateTime(TypeDecorator):
    """``DateTime(timezone=True)`` that actually round-trips tz-aware on SQLite.

    SQLAlchemy's sqlite dialect stores/parses ``DATETIME`` as a naive string
    regardless of ``timezone=True`` — on that backend the flag alone is a
    no-op (Postgres's real ``TIMESTAMPTZ`` doesn't have this problem, but
    SQLite is this project's default/only-tested backend). Every value this
    app writes is already UTC (``datetime.now(UTC)`` / ``CanonicalModel.
    _utcnow()``), so reattaching UTC tzinfo on both write and read is safe.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


class CanonicalRecord(SQLModel, table=True):
    """One row per synced/created canonical entity.

    Lineage and sync fields are real columns (indexed, used for dedup and
    incremental sync); the full domain payload is stored verbatim as JSON so the
    canonical model round-trips byte-for-byte.
    """

    __tablename__ = "canonical_record"
    __table_args__ = (
        UniqueConstraint(
            "workspace",
            "connector",
            "vendor_type",
            "vendor_id",
            name="uq_canonical_source",
        ),
    )

    pk: str = Field(primary_key=True)  # CanonicalModel.id
    workspace: str = Field(default="default", index=True)
    model_type: str = Field(index=True)  # e.g. "Initiative", "CustomerFeedback"
    connector: str
    vendor_type: str
    vendor_id: str | None = Field(default=None, index=True)  # None for manual records
    raw_fingerprint: str | None = Field(default=None)
    ingested_at: datetime = Field(sa_column=Column(UTCDateTime()))
    updated_at: datetime = Field(sa_column=Column(UTCDateTime()))
    payload: dict = Field(sa_column=Column(JSON))  # model_dump(mode="json")


class SyncStateRecord(SQLModel, table=True):
    """One row per connector: its last persisted incremental-sync cursor.

    The cursor is stored as a plain string (the opaque vendor token's ``value``),
    not a ``SyncCursor`` — the storage layer must not import a connector type
    (the connectors-isolation contract). The app converts to/from ``SyncCursor``.
    """

    __tablename__ = "sync_state"

    workspace: str = Field(default="default", primary_key=True)
    connector_key: str = Field(primary_key=True)
    cursor_value: str | None = Field(default=None)
    updated_at: datetime = Field(sa_column=Column(UTCDateTime()))
