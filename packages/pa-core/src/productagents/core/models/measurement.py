"""Measurement context: metric definitions and their observed values."""

from datetime import datetime

from pydantic import Field

from productagents.core.ids import MetricSnapshotId, ProductMetricId, new_id
from productagents.core.models._base import CanonicalModel


class ProductMetric(CanonicalModel):
    """The definition of a product metric (not a value)."""

    id: ProductMetricId = Field(default_factory=lambda: ProductMetricId(new_id()))
    name: str
    description: str = ""
    unit: str | None = None


class MetricSnapshot(CanonicalModel):
    """A single observed value of a ProductMetric at a point in time."""

    id: MetricSnapshotId = Field(default_factory=lambda: MetricSnapshotId(new_id()))
    metric_id: ProductMetricId | None = None
    value: float
    captured_at: datetime | None = None
