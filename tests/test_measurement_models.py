from datetime import UTC, datetime

from productagents.core.models.measurement import MetricSnapshot, ProductMetric


def test_metric_and_snapshot_link():
    metric = ProductMetric(name="Activation rate", unit="percent")
    snap = MetricSnapshot(
        metric_id=metric.id,
        value=42.5,
        captured_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    assert snap.metric_id == metric.id
    assert snap.value == 42.5
    assert MetricSnapshot.model_validate_json(snap.model_dump_json()) == snap
