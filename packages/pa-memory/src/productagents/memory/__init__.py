"""ProductAgents organizational memory subsystem.

The package's import surface is deliberately lightweight: only the pure JSONL
log helpers and the lexical retriever live here. The DB-backed ``LearningService``
/ ``DecisionStore`` / ``Embedder`` are imported from their submodules
(``productagents.memory.service`` etc.) so that ``import productagents.memory``
never pulls SQLAlchemy — keeping the agents→storage import contract enforceable.
"""

from productagents.memory.jsonl import (
    read_decisions,
    read_outcomes,
    record_decision,
    record_outcome,
)
from productagents.memory.retrieval import select_relevant_lessons

__all__ = [
    "read_decisions",
    "read_outcomes",
    "record_decision",
    "record_outcome",
    "select_relevant_lessons",
]
