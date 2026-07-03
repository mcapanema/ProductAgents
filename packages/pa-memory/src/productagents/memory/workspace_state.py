"""Workspace-state stores: configuration, connector config, and preferences.

Like ``EventStore``, the ``AsyncSession`` is injected by the platform boundary —
this module builds no engine. Rows are primitive KV/JSON; the *meaning* of keys
(whitelists, env-var mapping, precedence) lives a layer above in
``platform.configuration``, keeping pa-memory below pa-platform in the DAG.
Secret values must never be written here — connector blocks reference secrets
as ``<field>_env`` names only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from productagents.memory.tables import (
    ConnectorConfigRow,
    PreferenceRow,
    WorkspaceConfigRow,
    WorkspaceRow,
)

_L = list  # ponytail: 'list' method shadows the builtin under ty; alias keeps it honest


def _now() -> str:
    return datetime.now(UTC).isoformat()


class WorkspaceConfigStore:
    """Workspace configuration values (friendly key -> env-shaped string)."""

    def __init__(self, session: AsyncSession, workspace: str = "default") -> None:
        self._session = session
        self._workspace = workspace

    async def all(self) -> dict[str, str]:
        rows = (
            await self._session.execute(
                select(WorkspaceConfigRow).where(
                    WorkspaceConfigRow.workspace == self._workspace
                )
            )
        ).scalars()
        return {row.key: row.value for row in rows}

    async def set(self, key: str, value: str) -> None:
        await self._session.merge(
            WorkspaceConfigRow(
                workspace=self._workspace, key=key, value=value, updated_at=_now()
            )
        )
        await self._session.commit()

    async def delete(self, key: str) -> None:
        await self._session.execute(
            delete(WorkspaceConfigRow).where(
                WorkspaceConfigRow.workspace == self._workspace,
                WorkspaceConfigRow.key == key,
            )
        )
        await self._session.commit()


class ConnectorConfigStore:
    """Raw connector config blocks (registry key -> dict, YAML-block shaped)."""

    def __init__(self, session: AsyncSession, workspace: str = "default") -> None:
        self._session = session
        self._workspace = workspace

    async def all(self) -> dict[str, dict]:
        rows = (
            await self._session.execute(
                select(ConnectorConfigRow).where(
                    ConnectorConfigRow.workspace == self._workspace
                )
            )
        ).scalars()
        return {row.connector: row.config for row in rows}

    async def set(self, connector: str, config: dict) -> None:
        await self._session.merge(
            ConnectorConfigRow(
                workspace=self._workspace,
                connector=connector,
                config=config,
                updated_at=_now(),
            )
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


class WorkspaceRegistry:
    """The workspace registry rows: one per project/team scope."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> _L[dict[str, Any]]:
        rows = (
            await self._session.execute(
                select(WorkspaceRow).order_by(WorkspaceRow.name)
            )
        ).scalars()
        return [{"name": r.name, "created_at": r.created_at} for r in rows]

    async def get(self, name: str) -> dict | None:
        row = await self._session.get(WorkspaceRow, name)
        return {"name": row.name, "created_at": row.created_at} if row else None

    async def create(self, name: str) -> dict:
        if await self._session.get(WorkspaceRow, name) is not None:
            raise ValueError(f"workspace already exists: {name}")
        row = WorkspaceRow(name=name, created_at=_now())
        self._session.add(row)
        await self._session.commit()
        return {"name": row.name, "created_at": row.created_at}

    async def ensure(self, name: str) -> None:
        if await self._session.get(WorkspaceRow, name) is None:
            self._session.add(WorkspaceRow(name=name, created_at=_now()))
            await self._session.commit()
