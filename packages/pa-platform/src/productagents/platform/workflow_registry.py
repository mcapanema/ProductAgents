"""Workflow discovery via Python entry points (mirrors connectors/registry.py).

Workflows register under the ``productagents.workflows`` group, so a future
workflow (roadmap prioritization, quarterly planning, …) is added by declaring
an entry point — zero edits to WorkflowService or any presentation adapter. Each
entry point resolves to a *builder*: ``build(model, *, recorder, human_in_the_loop,
persist_events) -> Workflow``. Discovery is metadata-only until a builder is loaded.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from productagents.platform.workflow import Workflow

logger = logging.getLogger(__name__)

_GROUP = "productagents.workflows"

WorkflowBuilder = Callable[..., "Workflow"]


def discover() -> dict[str, WorkflowBuilder]:
    """Map every installed workflow's entry-point name to its builder.

    A broken third-party plugin is skipped (logged), never fatal — startup must
    survive one bad ``ep.load()``.
    """
    found: dict[str, WorkflowBuilder] = {}
    for ep in entry_points(group=_GROUP):
        try:
            found[ep.name] = ep.load()
        except Exception:  # noqa: BLE001 — one bad plugin must not break discovery
            logger.warning(
                "workflow plugin %r failed to load; skipping", ep.name, exc_info=True
            )
    return found
