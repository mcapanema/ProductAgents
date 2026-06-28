"""The graph↔store boundary: open a per-run session, wire services, run.

Keeps graph nodes engine-free (like `recall` keeps them log-free). The engine is
process-wide; each decision run gets its own short-lived session whose lifetime
spans the event stream, so the Knowledge Services read a consistent local
snapshot of the canonical store the connectors populated out of band.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from productagents.agents.context import AgentContext
from productagents.knowledge import build_services
from productagents.knowledge.repositories.sqlmodel.engine import (
    make_engine,
    make_sessionmaker,
)
from productagents.memory.embedding import HashingEmbedder
from productagents.memory.event_store import EventStore
from productagents.memory.service import LearningService
from productagents.memory.store import DecisionStore

# ponytail: one process-wide engine over the local SQLite file. Pool/replace per
# request if this ever serves concurrent decision runs.
_engine = None

# ponytail: one process-wide placeholder embedder. Swap for a real model behind
# the Embedder protocol in Phase 7; no caller changes.
_EMBEDDER = HashingEmbedder()


def get_engine():
    """Lazily build and cache the process-wide async engine."""
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


@asynccontextmanager
async def open_agent_context(
    model, *, session_factory=None
) -> AsyncIterator[AgentContext]:
    """Yield an AgentContext bound to one DB session for the duration of a run."""
    factory = session_factory or make_sessionmaker(get_engine())
    async with factory() as session:
        services = build_services(session)
        learning = LearningService(DecisionStore(session), _EMBEDDER)
        yield AgentContext(model=model, feedback=services.feedback, learning=learning)


@asynccontextmanager
async def open_event_store(*, engine=None) -> AsyncIterator[EventStore]:
    """Yield an EventStore bound to one DB session (mirrors open_agent_context)."""
    maker = make_sessionmaker(engine or get_engine())
    async with maker() as session:
        yield EventStore(session)


def _sessionmaker(engine):
    return make_sessionmaker(engine or get_engine())


def make_recorder(*, engine=None):
    """Async recorder: persist a full DecisionRecord to the memory store."""
    maker = _sessionmaker(engine)

    async def recorder(record) -> None:
        async with maker() as session:
            await LearningService(DecisionStore(session), _EMBEDDER).record_decision(
                record
            )

    return recorder


def make_outcome_recorder(*, engine=None):
    """Async outcome recorder: persist a reflected OutcomeRecord."""
    maker = _sessionmaker(engine)

    async def outcome_recorder(outcome) -> None:
        async with maker() as session:
            await LearningService(DecisionStore(session), _EMBEDDER).record_outcome(
                outcome
            )

    return outcome_recorder


def make_decision_reader(*, engine=None):
    """Async reader: list persisted decisions (for the reflection picker)."""
    maker = _sessionmaker(engine)

    async def reader() -> list:
        async with maker() as session:
            return await DecisionStore(session).decisions()

    return reader
