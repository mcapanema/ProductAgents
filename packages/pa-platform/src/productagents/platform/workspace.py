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
from dataclasses import dataclass
from pathlib import Path

from productagents.core.config import load_env

_L = list  # ponytail: method named 'list' shadows the builtin under ty

DEFAULT_WORKSPACE = "default"


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

        ``name`` defaults to ``PRODUCTAGENTS_WORKSPACE`` then ``DEFAULT_WORKSPACE``.
        """
        name = name or os.environ.get("PRODUCTAGENTS_WORKSPACE") or DEFAULT_WORKSPACE
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
