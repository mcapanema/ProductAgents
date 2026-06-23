"""The base shared by every synced canonical model."""

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime

from pydantic import BaseModel, Field, JsonValue

from productagents.core.ids import CanonicalId, new_id
from productagents.core.refs import SourceRef


def _utcnow() -> datetime:
    return datetime.now(UTC)


def fingerprint(payload: Mapping[str, object]) -> str:
    """Stable SHA-256 of a source payload, for incremental-sync change detection.

    Key order is normalized so the same logical payload always hashes the same.
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class CanonicalModel(BaseModel):
    """Platform-owned base for synced product entities.

    Carries the lineage spine (`source`), a stable platform id distinct from any
    vendor id, sync timestamps, a payload fingerprint for incremental sync, and an
    `extensions` escape hatch for vendor-specific extras. **Agents reason over the
    domain fields only — never `source`, `extensions`, or the sync metadata.**
    """

    id: CanonicalId = Field(default_factory=lambda: CanonicalId(new_id()))
    source: SourceRef = Field(default_factory=SourceRef.manual)
    ingested_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    raw_fingerprint: str | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)
