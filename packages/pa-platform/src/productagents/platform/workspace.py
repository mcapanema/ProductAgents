"""WorkspaceService — a Workspace is one product organization's local home.

A workspace is just a *directory*. It owns that organization's canonical store
(SQLite file), connector config, settings/secrets (``.env``), and logs. Isolation
is by filesystem path — there are no shared-database tenant keys — which keeps the
platform local-first while leaving room to map a workspace onto a per-tenant
volume if this ever grows a server.

Activation is deliberately thin: the engine, connector loader, and logging config
already read their paths from ``PRODUCTAGENTS_DB_URL`` /
``PRODUCTAGENTS_CONNECTORS_FILE`` / ``PRODUCTAGENTS_LOG_FILE``. ``activate``
points those at the workspace directory (via ``setdefault``, so an explicit
shell export still wins) and loads the workspace's ``.env``. Nothing downstream
needs to know workspaces exist.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from productagents.core.config import load_env

_L = list  # ponytail: 'list' method shadows the builtin under ty; alias keeps it honest

DEFAULT_WORKSPACE = "default"

_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


class WorkspaceError(ValueError):
    """Invalid workspace operation: bad name, duplicate create, unknown name."""


def _default_home() -> Path:
    """The directory holding all workspaces. Override with ``PRODUCTAGENTS_HOME``."""
    raw = os.environ.get("PRODUCTAGENTS_HOME")
    base = Path(raw).expanduser() if raw else Path.home() / ".productagents"
    return base / "workspaces"


@dataclass(frozen=True)
class Workspace:
    """A named local home for one product organization's state."""

    name: str
    root: Path

    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.root / 'productagents.db'}"

    @property
    def connectors_file(self) -> Path:
        return self.root / "connectors.yaml"

    @property
    def env_file(self) -> Path:
        return self.root / ".env"

    @property
    def log_file(self) -> Path:
        return self.root / "productagents.log"

    @property
    def prompts_dir(self) -> Path:
        return self.root / "prompts"


class WorkspaceService:
    def __init__(self, home: Path | None = None) -> None:
        self._home = home if home is not None else _default_home()

    def home(self) -> Path:
        return self._home

    def list(self) -> _L[Workspace]:
        if not self._home.exists():
            return []
        return [
            Workspace(name=child.name, root=child)
            for child in sorted(self._home.iterdir())
            if child.is_dir()
        ]

    def get(self, name: str) -> Workspace | None:
        root = self._home / name
        return Workspace(name=name, root=root) if root.is_dir() else None

    def resolve(self, name: str | None = None) -> Workspace:
        """Return the active workspace, creating its directory if absent.

        Precedence: explicit ``name`` > ``PRODUCTAGENTS_WORKSPACE`` > the
        persisted ``.active`` marker > ``DEFAULT_WORKSPACE``.
        """
        name = name or os.environ.get("PRODUCTAGENTS_WORKSPACE") or self.active_name()
        root = self._home / name
        root.mkdir(parents=True, exist_ok=True)
        return Workspace(name=name, root=root)

    def activate(self, workspace: Workspace) -> None:
        """Point the rest of the platform at ``workspace``.

        Sets the path env vars the storage/connector/logging layers already honor
        (``setdefault`` so an explicit shell export wins) and loads the
        workspace's ``.env`` for its settings/secrets.
        """
        os.environ.setdefault("PRODUCTAGENTS_DB_URL", workspace.db_url)
        os.environ.setdefault(
            "PRODUCTAGENTS_CONNECTORS_FILE", str(workspace.connectors_file)
        )
        os.environ.setdefault("PRODUCTAGENTS_LOG_FILE", str(workspace.log_file))
        os.environ.setdefault("PRODUCTAGENTS_PROMPTS_DIR", str(workspace.prompts_dir))
        if workspace.env_file.exists():
            load_env(dotenv_path=workspace.env_file)

    def create(self, name: str) -> Workspace:
        """Create a new workspace directory. Raises WorkspaceError on a bad
        or duplicate name."""
        if not _NAME_RE.fullmatch(name):
            raise WorkspaceError(
                f"invalid workspace name: {name!r} "
                "(letters/digits, then letters/digits/._-, max 64 chars)"
            )
        root = self._home / name
        if root.exists():
            raise WorkspaceError(f"workspace already exists: {name}")
        root.mkdir(parents=True)
        return Workspace(name=name, root=root)

    def _active_file(self) -> Path:
        # ponytail: a one-line marker file, not a registry DB — list() ignores
        # it because it only globs directories.
        return self._home / ".active"

    def active_name(self) -> str:
        """The persisted active workspace name (DEFAULT_WORKSPACE if unset)."""
        try:
            name = self._active_file().read_text(encoding="utf-8").strip()
        except OSError:
            return DEFAULT_WORKSPACE
        return name or DEFAULT_WORKSPACE

    def set_active(self, name: str) -> Workspace:
        """Persist ``name`` as the active workspace. It must already exist."""
        ws = self.get(name)
        if ws is None:
            raise WorkspaceError(f"no such workspace: {name}")
        self._home.mkdir(parents=True, exist_ok=True)
        self._active_file().write_text(ws.name + "\n", encoding="utf-8")
        return ws
