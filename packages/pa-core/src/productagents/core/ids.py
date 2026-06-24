"""Platform-owned, branded identifiers.

`NewType` gives static (ty/pyright) protection against mixing id kinds while
remaining a plain `str` at runtime, so Pydantic validates them as strings and
JSON serialization is unchanged.
"""

from typing import NewType
from uuid import uuid4


def new_id() -> str:
    """Generate a fresh platform-owned identifier (32-char hex)."""
    return uuid4().hex


CanonicalId = NewType("CanonicalId", str)
InitiativeId = NewType("InitiativeId", str)
FeatureId = NewType("FeatureId", str)
RoadmapItemId = NewType("RoadmapItemId", str)
FeedbackId = NewType("FeedbackId", str)
SupportTicketId = NewType("SupportTicketId", str)
UserSegmentId = NewType("UserSegmentId", str)
IncidentId = NewType("IncidentId", str)
ObjectiveId = NewType("ObjectiveId", str)
KeyResultId = NewType("KeyResultId", str)
ProductMetricId = NewType("ProductMetricId", str)
MetricSnapshotId = NewType("MetricSnapshotId", str)
