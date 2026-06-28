"""A Session = one execution of a workflow. The unit the streaming UI tracks."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

SessionStatus = Literal["running", "awaiting_approval", "finished", "failed"]


@dataclass
class Session:
    id: str
    workflow: str
    status: SessionStatus = "running"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
