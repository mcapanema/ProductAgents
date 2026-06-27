"""The sync runtime: concurrency + degrade-don't-crash."""

from typing import cast

from productagents.connectors.base import Connector, SyncCursor
from productagents.connectors.runtime import run_sync
from tests.connector_fakes import FailingConnector, FakeSink, WritingConnector


async def test_run_sync_aggregates_results_in_order():
    sink = FakeSink()
    connectors = [WritingConnector("a", 2, sink), WritingConnector("b", 3, sink)]

    results = await run_sync(cast(list[Connector], connectors))

    assert [r.connector for r in results] == ["a", "b"]
    assert [r.written for r in results] == [2, 3]
    assert all(r.ok for r in results)
    assert len(sink.written) == 5


async def test_one_failure_degrades_only_itself():
    sink = FakeSink()
    connectors = [
        WritingConnector("a", 2, sink),
        FailingConnector("b", sink),
        WritingConnector("c", 1, sink),
    ]

    results = await run_sync(cast(list[Connector], connectors))

    by_key = {r.connector: r for r in results}
    assert by_key["a"].ok
    assert by_key["a"].written == 2
    assert by_key["c"].ok
    assert by_key["c"].written == 1
    assert by_key["b"].ok is False
    assert by_key["b"].error is not None
    assert "boom" in by_key["b"].error
    assert len(sink.written) == 3  # a + c still wrote; b wrote nothing


async def test_cursor_is_threaded_per_connector():
    sink = FakeSink()
    seen: dict[str, SyncCursor | None] = {}

    class Recorder(WritingConnector):
        async def sync(self, cursor):
            seen[self.key] = cursor
            return await super().sync(cursor)

    connectors = [Recorder("a", 1, sink), Recorder("b", 1, sink)]
    await run_sync(
        cast(list[Connector], connectors), cursors={"a": SyncCursor(value="since-a")}
    )

    assert seen["a"] is not None
    assert seen["a"].value == "since-a"
    assert seen["b"] is None


async def test_run_sync_logs_a_span_per_connector(caplog):
    import logging

    sink = FakeSink()
    with caplog.at_level(logging.INFO, logger="productagents.connectors"):
        await run_sync(cast(list[Connector], [WritingConnector("a", 2, sink)]))
    messages = [r.getMessage() for r in caplog.records]
    assert any(
        m.startswith("connector.sync ") and "connector=a" in m and "written=2" in m
        for m in messages
    )


async def test_raised_failure_gets_classified_friendly_message():
    sink = FakeSink()
    results = await run_sync(cast(list[Connector], [FailingConnector("b", sink)]))
    # FailingConnector raises RuntimeError("boom") → UNKNOWN category friendly text.
    assert results[0].ok is False
    assert results[0].error is not None
    assert "The connector call failed" in results[0].error
