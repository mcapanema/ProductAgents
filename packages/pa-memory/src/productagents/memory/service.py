"""LearningService — the organizational-memory subsystem's Knowledge-Service face.

Agents and the app talk to this; it owns the embedding lifecycle (embed on
record) and the retrieval policy (lexical + semantic hybrid on read). It is NOT
re-exported from ``productagents.memory.__init__`` on purpose: importing it pulls
SQLAlchemy, so consumers import it from this submodule, keeping
``import productagents.memory`` storage-free.
"""

from productagents.core.models import DecisionRecord, Initiative, OutcomeRecord
from productagents.memory.embedding import Embedder
from productagents.memory.retrieval import select_relevant_lessons, semantic_matches
from productagents.memory.store import DecisionStore


def _initiative_text(initiative: Initiative) -> str:
    return f"{initiative.title} {initiative.description}"


class LearningService:
    """Read lessons from past decisions; capture decisions and outcomes."""

    def __init__(self, store: DecisionStore, embedder: Embedder) -> None:
        self._store = store
        self._embedder = embedder

    async def relevant_lessons(
        self, initiative: Initiative, *, limit: int = 3
    ) -> list[str]:
        decisions = await self._store.decisions()
        if not decisions:
            return []
        outcomes = await self._store.outcomes()
        embeddings = await self._store.embeddings()
        query = self._embedder.embed(_initiative_text(initiative))
        also = frozenset(semantic_matches(query, embeddings))
        return select_relevant_lessons(
            initiative, decisions, outcomes, limit=limit, also_relevant=also
        )

    async def record_decision(self, decision: DecisionRecord) -> None:
        embedding = self._embedder.embed(_initiative_text(decision.initiative))
        await self._store.record(decision, embedding)

    async def record_outcome(self, outcome: OutcomeRecord) -> None:
        await self._store.record_outcome(outcome)

    async def decisions(self) -> list[DecisionRecord]:
        return await self._store.decisions()
