"""Workspace-scope schema: composite keys allow the same key per workspace."""

import pytest
from sqlalchemy.exc import IntegrityError

from productagents.knowledge.repositories.sqlmodel.engine import (
    make_engine,
    make_sessionmaker,
)
from productagents.memory.store import create_all
from productagents.memory.tables import (
    ConnectorConfigRow,
    WorkspaceConfigRow,
    WorkspaceRow,
)


async def _session():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    await create_all(engine)
    return make_sessionmaker(engine)()


async def test_same_config_key_allowed_in_two_workspaces():
    async with await _session() as session:
        session.add(
            WorkspaceConfigRow(workspace="a", key="model", value="x", updated_at="t")
        )
        session.add(
            WorkspaceConfigRow(workspace="b", key="model", value="y", updated_at="t")
        )
        await session.commit()


async def test_same_config_key_rejected_within_one_workspace():
    async with await _session() as session:
        session.add(
            WorkspaceConfigRow(workspace="a", key="model", value="x", updated_at="t")
        )
        await session.commit()
        session.add(
            WorkspaceConfigRow(workspace="a", key="model", value="y", updated_at="t")
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_same_connector_allowed_in_two_workspaces():
    async with await _session() as session:
        session.add(
            ConnectorConfigRow(
                workspace="a", connector="github", config={}, updated_at="t"
            )
        )
        session.add(
            ConnectorConfigRow(
                workspace="b", connector="github", config={}, updated_at="t"
            )
        )
        await session.commit()


async def test_workspace_registry_row_roundtrip():
    async with await _session() as session:
        session.add(WorkspaceRow(name="acme", created_at="t"))
        await session.commit()
        row = await session.get(WorkspaceRow, "acme")
        assert row is not None
        assert row.created_at == "t"
