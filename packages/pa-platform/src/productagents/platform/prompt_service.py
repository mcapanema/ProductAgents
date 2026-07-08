"""PromptService — the Application-Layer face of the Prompt Registry.

A thin facade over the agents' ``PromptStore`` so presentation adapters (CLI,
GUI) can browse, read, diff, edit, and roll back prompts without importing the
agents package. ``create`` builds a store bound to the active workspace's
``prompts/`` directory (via ``PRODUCTAGENTS_PROMPTS_DIR``, which
``WorkspaceService.activate`` already sets).
"""

from __future__ import annotations

from productagents.agents.prompts import PromptStore


class PromptService:
    def __init__(self, store: PromptStore) -> None:
        self._store = store

    @classmethod
    def create(cls, workspace: str = "default") -> PromptService:
        import os
        from pathlib import Path

        from productagents.platform.workspace import WorkspaceService

        prompts_dir = os.environ.get("PRODUCTAGENTS_PROMPTS_DIR")
        if prompts_dir:
            root = Path(prompts_dir) / workspace
        else:
            root = WorkspaceService().prompts_dir(workspace)
        return cls(PromptStore(prompts_dir=root))

    def names(self) -> list[str]:
        return self._store.names()

    def get(self, name: str) -> str:
        return self._store.get(name)

    def versions(self, name: str) -> list[int]:
        return self._store.versions(name)

    def read(self, name: str, version: int) -> str:
        return self._store.read_version(name, version)

    def diff(self, name: str, old: int, new: int) -> str:
        return self._store.diff(name, old, new)

    def save(self, name: str, text: str) -> int:
        return self._store.save_version(name, text)

    def rollback(self, name: str, version: int) -> int:
        return self._store.rollback(name, version)
