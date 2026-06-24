"""Canonical product-domain models — the platform's public vocabulary.

Import models from here (`from productagents.core.models import Initiative`), not
from the per-context submodules. This package replaces the v1 `core.schemas`
module and re-exports the same symbol names so existing call sites need only a
module-path change.
"""

from productagents.core.enums import (
    DebateSide,
    DecidedBy,
    FeatureStatus,
    IncidentStatus,
    InitiativeStatus,
    Priority,
    RiskLevel,
    Sentiment,
    Severity,
    TicketStatus,
    Verdict,
)
from productagents.core.ids import new_id
from productagents.core.models._base import CanonicalModel, fingerprint
from productagents.core.models.decision import (
    AnalystFindings,
    AnalystReport,
    DebateArgument,
    DebateTurn,
    DecisionRecord,
    Evidence,
    EvidenceSourceRef,
    GovernanceFinding,
    GovernanceVerdict,
    HumanDecision,
    JudgeFinding,
    JudgeVerdict,
    OutcomeRecord,
    Recommendation,
    Reflection,
    RiskAssessment,
    RiskFinding,
)
from productagents.core.models.discovery import (
    CustomerFeedback,
    Incident,
    SupportTicket,
    UserSegment,
)
from productagents.core.models.measurement import MetricSnapshot, ProductMetric
from productagents.core.models.planning import Feature, Initiative, RoadmapItem
from productagents.core.models.strategy import KeyResult, Objective
from productagents.core.refs import ExternalRef, SourceRef

__all__ = [
    "AnalystFindings",
    "AnalystReport",
    # base + helpers
    "CanonicalModel",
    # discovery
    "CustomerFeedback",
    "DebateArgument",
    "DebateSide",
    "DebateTurn",
    "DecidedBy",
    "DecisionRecord",
    "Evidence",
    # decision (v1 migrated)
    "EvidenceSourceRef",
    "ExternalRef",
    "Feature",
    "FeatureStatus",
    "GovernanceFinding",
    "GovernanceVerdict",
    "HumanDecision",
    "Incident",
    "IncidentStatus",
    # planning
    "Initiative",
    "InitiativeStatus",
    "JudgeFinding",
    "JudgeVerdict",
    "KeyResult",
    "MetricSnapshot",
    # strategy
    "Objective",
    "OutcomeRecord",
    "Priority",
    # measurement
    "ProductMetric",
    "Recommendation",
    "Reflection",
    "RiskAssessment",
    "RiskFinding",
    "RiskLevel",
    "RoadmapItem",
    "Sentiment",
    "Severity",
    # lineage
    "SourceRef",
    "SupportTicket",
    "TicketStatus",
    "UserSegment",
    # enums
    "Verdict",
    "fingerprint",
    "new_id",
]
