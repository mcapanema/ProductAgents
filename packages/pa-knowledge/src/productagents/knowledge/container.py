"""Service factory + DI assembly — the knowledge layer's entry point.

Hands callers a bundle of services wired to one session's repositories.
Consumers (agents, jobs, a future REST facade) depend on this bundle, never on
repositories or the engine. Phase 5 wraps it (plus the chat model) into the
agents' ``AgentContext``.
"""

from dataclasses import dataclass

from sqlmodel.ext.asyncio.session import AsyncSession

from productagents.core.models import CustomerFeedback, Initiative, ProductMetric
from productagents.knowledge.repositories.sqlmodel.canonical_repository import (
    CanonicalRepository,
)
from productagents.knowledge.services.feedback_service import FeedbackService
from productagents.knowledge.services.initiative_service import InitiativeService
from productagents.knowledge.services.metrics_service import MetricsService


@dataclass(frozen=True)
class KnowledgeServices:
    """The platform API surface handed to consumers."""

    feedback: FeedbackService
    initiatives: InitiativeService
    metrics: MetricsService


def build_services(session: AsyncSession) -> KnowledgeServices:
    """Wire every service to its repository over one session."""
    return KnowledgeServices(
        feedback=FeedbackService(CanonicalRepository(session, CustomerFeedback)),
        initiatives=InitiativeService(CanonicalRepository(session, Initiative)),
        metrics=MetricsService(CanonicalRepository(session, ProductMetric)),
    )
