"""The Prompt Registry: prompts are named, versioned, overridable assets.

A prompt is a ``string.Template`` ($slot placeholders). ``get`` resolves a name
to its active template text — the workspace's highest-numbered override version
if one exists, else the bundled default shipped with this package. ``render``
substitutes the dynamic strings the node helpers build. Substitution inserts
values *literally* (no re-scan), so untrusted evidence/transcript text that
contains ``{`` or ``$`` is safe.

Storage is append-only: the bundled default is version 0; each workspace edit is
a new numbered file under ``<prompts_dir>/<name>/NNNN.txt``; active = the highest
number; rollback re-appends an old version. The workspace points
``PRODUCTAGENTS_PROMPTS_DIR`` at its own ``prompts/`` dir, mirroring how the DB
url and log path are wired — so a node-side store picks it up with no plumbing.
"""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path
from string import Template

# ponytail: data lives beside this package, reached by path (never imported).
_DEFAULTS = files("productagents.agents").joinpath("prompts", "defaults")


class PromptStore:
    def __init__(self, prompts_dir: Path | str | None = None) -> None:
        raw = (
            prompts_dir
            if prompts_dir is not None
            else os.environ.get("PRODUCTAGENTS_PROMPTS_DIR")
        )
        self._dir = Path(raw) if raw else None

    # ---- read path (used by graph nodes) -------------------------------
    def get(self, name: str) -> str:
        version = self.active_version(name)
        return self.read_version(name, version)

    def render(self, name: str, /, **values: object) -> str:
        return Template(self.get(name)).substitute(**values)

    # ---- bundled defaults ----------------------------------------------
    def _bundled(self, name: str) -> str:
        resource = _DEFAULTS.joinpath(f"{name}.txt")
        try:
            return resource.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError) as exc:
            raise KeyError(f"unknown prompt: {name!r}") from exc

    def active_version(self, name: str) -> int:
        return 0  # Task 2 replaces this with override-dir resolution

    def read_version(self, name: str, version: int) -> str:
        if version == 0:
            return self._bundled(name)
        raise KeyError(f"no version {version} for {name!r}")  # Task 2 fills this
