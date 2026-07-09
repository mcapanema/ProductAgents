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
    _utcnow()``), so reattaching UTC tzinfo on read is safe; on write, any
    aware value is normalized to UTC first (SQLite stores only the wall-clock
    digits, so a non-UTC offset must be converted, not just tagged, or it
    silently round-trips as the wrong instant).
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if value.tzinfo is None:
            # ponytail: naive input is treated as already-UTC, never converted.
            # Every current writer (_utcnow(), SyncStateStore.save()) produces
            # UTC-aware datetimes, so this branch only exists to correctly read
            # back legacy rows written naive before commit 649ab16.
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

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
    # Deduplication identity: on upsert, records are matched by
    # (workspace, connector, vendor_type, vendor_id) for synced sources, or by
    # platform_id alone for manual records. This ensures that the same canonical
    # entity (same source + same external ID) maps to exactly one row, and
    # re-syncs preserve the platform_id across updates.
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
