"""WorkspaceService — a workspace is a logical scope (project/team), not a directory.

All workspaces share one home: one SQLite DB, one ``.env`` (secrets), one log.
Isolation is a ``workspace`` key scoping rows (see pa-memory / pa-knowledge
stores); the registry of workspaces is the ``workspace`` table. Only prompt
overrides live per-workspace on disk (``<home>/prompts/<name>/``), and the
persisted active-workspace name is a marker file so the CLI can resolve it
synchronously before any engine exists.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from productagents.core._typing import List as _L
from productagents.core.config import load_env

logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE = "default"

_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


class WorkspaceError(ValueError):
    """Invalid workspace operation: bad name, duplicate create, unknown name."""


@dataclass(frozen=True)
class SharedHome:
    """The one directory every workspace shares."""

    root: Path

    @property
    def db_path(self) -> Path:
        return self.root / "productagents.db"

    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"

    @property
    def env_file(self) -> Path:
        return self.root / ".env"

    @property
    def log_file(self) -> Path:
        return self.root / "productagents.log"

    @property
    def connectors_file(self) -> Path:
        return self.root / "connectors.yaml"

    @property
    def prompts_root(self) -> Path:
        return self.root / "prompts"

    @property
    def active_file(self) -> Path:
        return self.root / ".active"

    @property
    def legacy_workspaces_dir(self) -> Path:
        return self.root / "workspaces"


def default_home() -> SharedHome:
    raw = os.environ.get("PRODUCTAGENTS_HOME")
    root = Path(raw).expanduser() if raw else Path.home() / ".productagents"
    return SharedHome(root=root)


def _validate(name: str) -> str:
    if not _NAME_RE.fullmatch(name):
        raise WorkspaceError(
            f"invalid workspace name: {name!r} "
            "(letters/digits, then letters/digits/._-, max 64 chars)"
        )
    return name


class WorkspaceService:
    def __init__(self, home: SharedHome | None = None, engine=None) -> None:
        self._home = home if home is not None else default_home()
        self._engine = engine  # test seam; None -> process-wide engine

    def home(self) -> SharedHome:
        return self._home

    # -- sync bootstrap surface (no DB) -------------------------------------

    def resolve(self, name: str | None = None) -> str:
        """The active workspace NAME. Precedence: explicit > env > marker > default."""
        name = name or os.environ.get("PRODUCTAGENTS_WORKSPACE") or self.active_name()
        return _validate(name)

    def activate(self) -> None:
        """Point the platform at the shared home (setdefault; exports win)."""
        self._home.root.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("PRODUCTAGENTS_DB_URL", self._home.db_url)
        os.environ.setdefault(
            "PRODUCTAGENTS_CONNECTORS_FILE", str(self._home.connectors_file)
        )
        os.environ.setdefault("PRODUCTAGENTS_LOG_FILE", str(self._home.log_file))
        os.environ.setdefault("PRODUCTAGENTS_PROMPTS_DIR", str(self._home.prompts_root))
        if self._home.env_file.exists():
            load_env(dotenv_path=self._home.env_file)

    def active_name(self) -> str:
        try:
            name = self._home.active_file.read_text(encoding="utf-8").strip()
        except OSError:
            return DEFAULT_WORKSPACE
        return name or DEFAULT_WORKSPACE

    def _write_marker(self, name: str) -> None:
        self._home.root.mkdir(parents=True, exist_ok=True)
        self._home.active_file.write_text(name + "\n", encoding="utf-8")

    def prompts_dir(self, name: str) -> Path:
        return self._home.prompts_root / name

    # -- async registry surface (DB) -----------------------------------------

    def _sessionmaker(self):
        from productagents.knowledge.repositories.sqlmodel.engine import (
            make_sessionmaker,
        )
        from productagents.platform.context import get_engine

        return make_sessionmaker(self._engine or get_engine())

    async def list(self) -> _L[dict]:
        from productagents.memory.workspace_state import WorkspaceRegistry

        async with self._sessionmaker()() as session:
            return await WorkspaceRegistry(session).list()

    async def get(self, name: str) -> dict | None:
        from productagents.memory.workspace_state import WorkspaceRegistry

        async with self._sessionmaker()() as session:
            return await WorkspaceRegistry(session).get(name)

    async def create(self, name: str) -> dict:
        from productagents.memory.workspace_state import WorkspaceRegistry

        _validate(name)
        async with self._sessionmaker()() as session:
            try:
                return await WorkspaceRegistry(session).create(name)
            except ValueError as exc:
                raise WorkspaceError(str(exc)) from exc

    async def set_active(self, name: str) -> dict:
        _validate(name)
        row = await self.get(name)
        if row is None:
            raise WorkspaceError(f"no such workspace: {name}")
        self._write_marker(name)
        return row

    async def ensure_default(self) -> None:
        from productagents.memory.workspace_state import WorkspaceRegistry

        async with self._sessionmaker()() as session:
            await WorkspaceRegistry(session).ensure(DEFAULT_WORKSPACE)

    async def rename(self, old: str, new: str) -> dict:
        """Rename a workspace: registry row, every scoped row, prompts dir, marker.

        The DB side runs as ONE transaction (both storage packages' helpers,
        one commit) so data can never split across two names. The filesystem
        tail (prompts dir, marker) runs after commit and degrades on failure —
        worst case the prompt overrides sit under the old directory name.
        """
        _validate(old)
        _validate(new)
        if await self.get(old) is None:
            raise WorkspaceError(f"no such workspace: {old}")
        if await self.get(new) is not None:
            raise WorkspaceError(f"workspace already exists: {new}")
        from productagents.knowledge import rename_workspace as rename_canonical
        from productagents.memory.workspace_state import (
            rename_workspace as rename_memory,
        )

        async with self._sessionmaker()() as session:
            await rename_memory(session, old, new)
            await rename_canonical(session, old, new)
            await session.commit()

        old_prompts = self.prompts_dir(old)
        if old_prompts.is_dir():
            try:
                os.replace(old_prompts, self.prompts_dir(new))
            except OSError:
                logger.error(
                    "prompts dir move failed renaming %s -> %s", old, new, exc_info=True
                )
        if self.active_name() == old:
            self._write_marker(new)
        row = await self.get(new)
        return row if row is not None else {"name": new, "created_at": ""}
