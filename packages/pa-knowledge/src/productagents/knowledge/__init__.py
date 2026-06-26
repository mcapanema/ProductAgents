"""ProductAgents knowledge layer.

Phase 2 ships the storage spine: a generic canonical store, a swappable
``Repository`` protocol, and the connector-facing ``CanonicalSink``. Phase 3
adds the product-question services on top.
"""

from productagents.knowledge.config import database_url
from productagents.knowledge.repositories._base import Repository
from productagents.knowledge.repositories.sqlmodel.canonical_repository import (
    CanonicalRepository,
)
from productagents.knowledge.repositories.sqlmodel.engine import (
    create_all,
    drop_all,
    make_engine,
    make_sessionmaker,
)
from productagents.knowledge.sink import CanonicalSink, DbCanonicalSink

__all__ = [
    "CanonicalRepository",
    "CanonicalSink",
    "DbCanonicalSink",
    "Repository",
    "create_all",
    "database_url",
    "drop_all",
    "make_engine",
    "make_sessionmaker",
]
