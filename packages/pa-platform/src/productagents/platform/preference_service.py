"""PreferenceService — user-experience preferences, workspace-owned.

Preferences affect the user experience, never workflow execution — which is why
they get their own store, whitelist, and IPC methods instead of routing through
``ConfigurationService``. Today's only key: ``theme``.
"""

from productagents.memory.store import create_all
from productagents.memory.workspace_state import PreferenceStore

_PREF_KEYS = frozenset({"theme"})


class PreferenceService:
    def __init__(self, *, engine=None) -> None:
        self._engine = engine

    def _sessionmaker(self):
        from productagents.knowledge.repositories.sqlmodel.engine import (
            make_sessionmaker,
        )
        from productagents.platform.context import get_engine

        return make_sessionmaker(self._engine or get_engine())

    async def _ensure_schema(self) -> None:
        from productagents.platform.context import get_engine

        await create_all(self._engine or get_engine())

    async def all(self) -> dict[str, str]:
        await self._ensure_schema()
        async with self._sessionmaker()() as session:
            return await PreferenceStore(session).all()

    async def set(self, key: str, value: str) -> dict[str, str]:
        if key not in _PREF_KEYS:
            valid = ", ".join(sorted(_PREF_KEYS))
            raise ValueError(f"unknown preference: {key!r} (valid: {valid})")
        await self._ensure_schema()
        async with self._sessionmaker()() as session:
            store = PreferenceStore(session)
            await store.set(key, str(value))
            return await store.all()
