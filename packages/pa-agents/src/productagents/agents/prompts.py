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

import difflib
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

    # ---- override directory layout: <dir>/<name>/NNNN.txt ---------------
    def _name_dir(self, name: str) -> Path | None:
        return self._dir / name if self._dir is not None else None

    def _override_versions(self, name: str) -> list[int]:
        d = self._name_dir(name)
        if d is None or not d.is_dir():
            return []
        return sorted(int(p.stem) for p in d.glob("[0-9]*.txt") if p.stem.isdigit())

    def active_version(self, name: str) -> int:
        overrides = self._override_versions(name)
        return overrides[-1] if overrides else 0

    def versions(self, name: str) -> list[int]:
        return [0, *self._override_versions(name)]

    def read_version(self, name: str, version: int) -> str:
        if version == 0:
            return self._bundled(name)
        d = self._name_dir(name)
        if d is None:
            raise KeyError(f"no override store for {name!r}")
        path = d / f"{version:04d}.txt"
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise KeyError(f"no version {version} for {name!r}") from exc

    def _validate_template(self, name: str, text: str) -> None:
        """Reject a template that would fail at render time.

        Two failure modes bite mid-run otherwise: a bare ``$`` (e.g. ``$5``)
        makes ``Template.substitute`` raise ``ValueError``, and an unknown
        ``$placeholder`` makes it raise ``KeyError``. We catch both here so a
        bad override never reaches disk (and never breaks an analyst).
        """
        tpl = Template(text)
        if not tpl.is_valid():
            raise ValueError(
                f"prompt {name!r} has an invalid $placeholder — "
                "use $$ for a literal dollar sign"
            )
        try:
            allowed = set(Template(self._bundled(name)).get_identifiers())
        except KeyError:
            return  # custom prompt with no bundled default: nothing to check against
        unknown = sorted(set(tpl.get_identifiers()) - allowed)
        if unknown:
            allowed_str = ", ".join(f"${a}" for a in sorted(allowed)) or "(none)"
            raise ValueError(
                f"prompt {name!r} uses unknown placeholder(s) "
                f"{', '.join(f'${u}' for u in unknown)}; allowed: {allowed_str}"
            )

    def save_version(self, name: str, text: str) -> int:
        if self._dir is None:
            raise RuntimeError("PromptStore has no writable prompts_dir")
        self._validate_template(name, text)
        d = self._dir / name
        d.mkdir(parents=True, exist_ok=True)
        # ponytail: exclusive create ("x") means a racing writer (GUI + CLI, or
        # two GUI windows) can never clobber a version file. On collision we
        # recompute the next number and retry — guaranteed to terminate because
        # active_version() strictly increases once the taken file exists.
        while True:
            version = self.active_version(name) + 1
            path = d / f"{version:04d}.txt"
            try:
                with open(path, "x", encoding="utf-8") as fh:
                    fh.write(text)
                return version
            except FileExistsError:
                continue

    def rollback(self, name: str, version: int) -> int:
        return self.save_version(name, self.read_version(name, version))

    def diff(self, name: str, old: int, new: int) -> str:
        a = self.read_version(name, old).splitlines(keepends=True)
        b = self.read_version(name, new).splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(a, b, fromfile=f"{name}@{old}", tofile=f"{name}@{new}")
        )

    def names(self) -> list[str]:
        bundled = {p.name.removesuffix(".txt") for p in _DEFAULTS.iterdir()}
        overrides: set[str] = set()
        if self._dir is not None and self._dir.is_dir():
            overrides = {c.name for c in self._dir.iterdir() if c.is_dir()}
        return sorted(bundled | overrides)
