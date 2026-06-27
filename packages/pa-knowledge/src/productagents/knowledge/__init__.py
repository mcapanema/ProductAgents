"""ProductAgents knowledge layer.

Phase 2 ships the storage spine: a generic canonical store, a swappable
``Repository`` protocol, and the connector-facing ``CanonicalSink``. Phase 3
adds the product-question services on top: typed ``*Query`` → ``Page`` of
canonical models, assembled by ``build_services``.
"""

from productagents.knowledge.config import database_url
from productagents.knowledge.container import KnowledgeServices, build_services
from productagents.knowledge.repositories._base import Repository
from productagents.knowledge.services._page import Page
from productagents.knowledge.services._query import Query
from productagents.knowledge.services.feedback_service import (
    FeedbackQuery,
    FeedbackService,
)
from productagents.knowledge.services.initiative_service import (
    InitiativeQuery,
    InitiativeService,
)
from productagents.knowledge.services.metrics_service import (
    MetricQuery,
    MetricsService,
)
from productagents.knowledge.sink import CanonicalSink, DbCanonicalSink
from productagents.knowledge.sync_state import SyncStateStore

__all__ = [
    "CanonicalSink",
    "DbCanonicalSink",
    "FeedbackQuery",
    "FeedbackService",
    "InitiativeQuery",
    "InitiativeService",
    "KnowledgeServices",
    "MetricQuery",
    "MetricsService",
    "Page",
    "Query",
    "Repository",
    "SyncStateStore",
    "build_services",
    "database_url",
]
