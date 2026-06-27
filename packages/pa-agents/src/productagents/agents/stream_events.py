"""The custom-stream contract between graph nodes and the runner.

Nodes emit progress through `get_writer()`; the runner parses it. The wire format
is a flat dict — LangGraph custom-mode chunks pass through unchanged. This module
is the single source of truth for the dict's keys and how each chunk is built, so
a key can't be misspelled in one place and silently dropped in another.

Every chunk carries `NODE`. The remaining keys are mutually-exclusive variants:
a `STATUS` progress line, an `ERROR` (optionally `FATAL` with a `CATEGORY`), or a
payload key (`TURN`/`ASSESSMENT`/`JUDGMENT`/`VERDICT`/`FINAL_VERDICT`) carrying a
model dump for live rendering. The runner (`runner._event_from_custom`) is the
matching consumer.
"""

from typing import Any

from pydantic import BaseModel

# Markers present on every / many chunks.
NODE = "node"
STATUS = "status"
ERROR = "error"
FATAL = "fatal"
CATEGORY = "category"

# Payload keys: each names the model dump a node emits for live rendering.
TURN = "turn"
ASSESSMENT = "assessment"
JUDGMENT = "judgment"
VERDICT = "verdict"
FINAL_VERDICT = "final_verdict"


def emit_status(node: str, message: str) -> dict[str, Any]:
    """A progress line for the node's panel."""
    return {NODE: node, STATUS: message}


def emit_error(node: str, message: str) -> dict[str, Any]:
    """A per-node degraded-failure line (the run continues)."""
    return {NODE: node, ERROR: message}


def emit_fatal(node: str, message: str, category: str) -> dict[str, Any]:
    """A systemic failure marker telling the runner to stop the run early."""
    return {NODE: node, ERROR: message, FATAL: True, CATEGORY: category}


def emit_payload(node: str, key: str, model: BaseModel) -> dict[str, Any]:
    """A render payload: the model dump under one of the payload keys."""
    return {NODE: node, key: model.model_dump()}
