"""The span() helper: structured, span-like logging without an OTel dependency."""

import logging

import pytest

from productagents.connectors.observability import span


def test_span_logs_name_duration_and_default_ok_status(caplog):
    with (
        caplog.at_level(logging.INFO, logger="productagents.connectors"),
        span("connector.sync", connector="github"),
    ):
        pass
    record = caplog.records[-1]
    assert record.getMessage().startswith("connector.sync ")
    assert "duration_ms=" in record.getMessage()
    assert "connector=github" in record.getMessage()
    assert "status=ok" in record.getMessage()


def test_span_attrs_set_inside_block_are_logged(caplog):
    with (
        caplog.at_level(logging.INFO, logger="productagents.connectors"),
        span("connector.sync", connector="github") as attrs,
    ):
        attrs["written"] = 7
    assert "written=7" in caplog.records[-1].getMessage()


def test_span_marks_error_status_and_reraises(caplog):
    with (
        caplog.at_level(logging.INFO, logger="productagents.connectors"),
        pytest.raises(ValueError, match="boom"),
        span("connector.health", connector="jira"),
    ):
        raise ValueError("boom")
    assert "status=error" in caplog.records[-1].getMessage()
