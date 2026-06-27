"""span() now lives in pa-core so both connectors and agents can use it."""

import logging

import pytest

from productagents.core.observability import span


def test_span_logs_name_duration_and_default_ok_status(caplog):
    with (
        caplog.at_level(logging.INFO, logger="productagents.observability"),
        span("decision.run", initiative="Add SSO"),
    ):
        pass
    msg = caplog.records[-1].getMessage()
    assert msg.startswith("decision.run ")
    assert "duration_ms=" in msg
    assert "initiative=Add SSO" in msg
    assert "status=ok" in msg


def test_span_attrs_set_inside_block_are_logged(caplog):
    with (
        caplog.at_level(logging.INFO, logger="productagents.observability"),
        span("decision.run") as attrs,
    ):
        attrs["reports"] = 5
    assert "reports=5" in caplog.records[-1].getMessage()


def test_span_marks_error_status_and_reraises(caplog):
    with (
        caplog.at_level(logging.INFO, logger="productagents.observability"),
        pytest.raises(ValueError, match="boom"),
        span("decision.debate"),
    ):
        raise ValueError("boom")
    assert "status=error" in caplog.records[-1].getMessage()
