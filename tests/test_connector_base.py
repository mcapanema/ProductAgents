"""The connector contract: value types + a minimal concrete Connector."""

import pytest

from productagents.connectors.base import (
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
)
from productagents.core.models import CustomerFeedback
from tests.connector_fakes import FakeSink


def test_value_types_default():
    assert SyncCursor().value is None
    assert SyncResult(connector="x").ok is True
    assert SyncResult(connector="x").written == 0
    assert HealthStatus(ok=True).detail == ""
    assert ConnectorConfig().enabled is True


def test_connector_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        Connector(ConnectorConfig(), FakeSink())  # abstract methods unimplemented


async def test_minimal_concrete_connector_roundtrips():
    class Echo(Connector):
        key = "echo"
        produces = frozenset({CustomerFeedback})

        async def health_check(self) -> HealthStatus:
            return HealthStatus(ok=True)

        async def sync(self, cursor: SyncCursor | None) -> SyncResult:
            await self.sink.write(CustomerFeedback(body="hi"))
            return SyncResult(
                connector=self.key, written=1, cursor=SyncCursor(value="t1")
            )

    sink = FakeSink()
    result = await Echo(ConnectorConfig(), sink).sync(None)

    assert result.connector == "echo"
    assert result.written == 1
    assert result.cursor is not None
    assert result.cursor.value == "t1"
    assert len(sink.written) == 1
    assert isinstance(sink.written[0], CustomerFeedback)
    assert sink.written[0].body == "hi"
    assert Echo.produces == frozenset({CustomerFeedback})
