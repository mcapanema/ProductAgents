"""The platform's stable, workflow-agnostic event vocabulary.

These frozen dataclasses are the single contract every presentation adapter
matches on. They wrap canonical ``core`` models as payloads but expose a
taxonomy that knows nothing about LangGraph or the agents package.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from productagents.core.models import (
    AnalystReport,
    DebateTurn,
    GovernanceVerdict,
    JudgeVerdict,
    Recommendation,
    RiskAssessment,
)


@dataclass(frozen=True, kw_only=True)
class Event:
    """Base for every platform event. ``seq`` orders events within a session."""

    session_id: str
    seq: int
    ts: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, kw_only=True)
class SessionStarted(Event):
    workflow: str


@dataclass(frozen=True, kw_only=True)
class NodeProgress(Event):
    node: str
    message: str


@dataclass(frozen=True, kw_only=True)
class AnalystCompleted(Event):
    node: str
    report: AnalystReport


@dataclass(frozen=True, kw_only=True)
class DebateTurnEmitted(Event):
    round: int
    side: str
    argument: str


@dataclass(frozen=True, kw_only=True)
class RiskAssessed(Event):
    reviewer: str
    role: str
    level: str
    rationale: str


@dataclass(frozen=True, kw_only=True)
class Recommended(Event):
    recommendation: Recommendation


@dataclass(frozen=True, kw_only=True)
class Judged(Event):
    passed: bool
    evidence_grounding_score: float
    rationale_coherence_score: float
    critique: str
    attempt: int


@dataclass(frozen=True, kw_only=True)
class GovernanceAdvised(Event):
    verdict: str
    rationale: str


@dataclass(frozen=True, kw_only=True)
class LessonsRecalled(Event):
    lessons: list[str]


@dataclass(frozen=True, kw_only=True)
class ApprovalRequested(Event):
    """Emitted when a HITL run interrupts for human approval."""

    advisory_verdict: str
    advisory_rationale: str


@dataclass(frozen=True, kw_only=True)
class FinalVerdict(Event):
    verdict: str
    rationale: str
    decided_by: str


@dataclass(frozen=True, kw_only=True)
class NodeFailed(Event):
    """A single node degraded (transient) — the run continues."""

    node: str
    message: str


@dataclass(frozen=True, kw_only=True)
class SessionFailed(Event):
    """A fatal error aborted the run (rate-limit/auth/tool-calling-unsupported)."""

    node: str
    category: str
    message: str


@dataclass(frozen=True, kw_only=True)
class SessionCancelled(Event):
    """A run was cancelled cooperatively at the user's request."""


@dataclass(frozen=True, kw_only=True)
class SessionFinished(Event):
    recommendation: Recommendation | None
    reports: list[AnalystReport]
    debate: list[DebateTurn]
    risks: list[RiskAssessment]
    governance: GovernanceVerdict | None
    prior_lessons: list[str]
    judgment: JudgeVerdict | None
