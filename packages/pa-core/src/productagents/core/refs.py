"""Lineage references: where a canonical record came from.

`SourceRef` records the connector + vendor entity + vendor id a canonical model
was mapped from. Agents must never read these for reasoning; they exist only for
traceability, dedup, and incremental-sync reconciliation. Manually-created
records (e.g. a user-typed Initiative) carry `SourceRef.manual()`.
"""

from pydantic import BaseModel


class SourceRef(BaseModel):
    """The connector + vendor record a canonical model was mapped from."""

    connector: str
    vendor_type: str
    vendor_id: str
    url: str | None = None

    @classmethod
    def manual(cls) -> SourceRef:
        """Provenance for platform/user-created records (no connector involved)."""
        return cls(connector="manual", vendor_type="manual", vendor_id="")


class ExternalRef(BaseModel):
    """A typed pointer to a record living in an external system."""

    system: str
    id: str
    url: str | None = None
