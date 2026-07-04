"""Canonical product-domain models — the platform's public vocabulary.

Import models from here (`from productagents.core.models import Initiative`), not
from the per-context submodules. This package is the v2 replacement for the v1
schemas module and re-exports the same symbol names so existing call sites need
only a module-path change.
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
from productagents.core.models.workflow import (
    END_ID,
    START_ID,
    WorkflowDefinition,
    WorkflowEdgeDef,
    WorkflowNodeDef,
)
from productagents.core.refs import ExternalRef, SourceRef

__all__ = [
    "END_ID",
    "START_ID",
    "AnalystFindings",
    "AnalystReport",
    "CanonicalModel",
    "CustomerFeedback",
    "DebateArgument",
    "DebateSide",
    "DebateTurn",
    "DecidedBy",
    "DecisionRecord",
    "Evidence",
    "EvidenceSourceRef",
    "ExternalRef",
    "Feature",
    "FeatureStatus",
    "GovernanceFinding",
    "GovernanceVerdict",
    "HumanDecision",
    "Incident",
    "IncidentStatus",
    "Initiative",
    "InitiativeStatus",
    "JudgeFinding",
    "JudgeVerdict",
    "KeyResult",
    "MetricSnapshot",
    "Objective",
    "OutcomeRecord",
    "Priority",
    "ProductMetric",
    "Recommendation",
    "Reflection",
    "RiskAssessment",
    "RiskFinding",
    "RiskLevel",
    "RoadmapItem",
    "Sentiment",
    "Severity",
    "SourceRef",
    "SupportTicket",
    "TicketStatus",
    "UserSegment",
    "Verdict",
    "WorkflowDefinition",
    "WorkflowEdgeDef",
    "WorkflowNodeDef",
    "fingerprint",
    "new_id",
]
