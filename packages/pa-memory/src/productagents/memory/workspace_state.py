"""Workspace-state stores: configuration, connector config, and preferences.

Like ``EventStore``, the ``AsyncSession`` is injected by the platform boundary —
this module builds no engine. Rows are primitive KV/JSON; the *meaning* of keys
(whitelists, env-var mapping, precedence) lives a layer above in
``platform.configuration``, keeping pa-memory below pa-platform in the DAG.
Secret values must never be written here — connector blocks reference secrets
as ``<field>_env`` names only.
"""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from productagents.memory.tables import (
    ConnectorConfigRow,
    PreferenceRow,
    WorkspaceConfigRow,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class WorkspaceConfigStore:
    """Workspace configuration values (friendly key -> env-shaped string)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def all(self) -> dict[str, str]:
        rows = (await self._session.execute(select(WorkspaceConfigRow))).scalars()
        return {row.key: row.value for row in rows}

    async def set(self, key: str, value: str) -> None:
        await self._session.merge(
            WorkspaceConfigRow(key=key, value=value, updated_at=_now())
        )
        await self._session.commit()

    async def delete(self, key: str) -> None:
        await self._session.execute(
            delete(WorkspaceConfigRow).where(WorkspaceConfigRow.key == key)
        )
        await self._session.commit()


class ConnectorConfigStore:
    """Raw connector config blocks (registry key -> dict, YAML-block shaped)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def all(self) -> dict[str, dict]:
        rows = (await self._session.execute(select(ConnectorConfigRow))).scalars()
        return {row.connector: row.config for row in rows}

    async def set(self, connector: str, config: dict) -> None:
        await self._session.merge(
            ConnectorConfigRow(connector=connector, config=config, updated_at=_now())
        )
        await self._session.commit()


class PreferenceStore:
    """User-experience preferences (key -> string). Never affects execution."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def all(self) -> dict[str, str]:
        rows = (await self._session.execute(select(PreferenceRow))).scalars()
        return {row.key: row.value for row in rows}

    async def get(self, key: str) -> str | None:
        row = await self._session.get(PreferenceRow, key)
        return row.value if row is not None else None

    async def set(self, key: str, value: str) -> None:
        await self._session.merge(
            PreferenceRow(key=key, value=value, updated_at=_now())
        )
        await self._session.commit()
