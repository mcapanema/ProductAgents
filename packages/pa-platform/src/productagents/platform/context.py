"""The graph↔store boundary: open a per-run session, wire services, run.

Keeps graph nodes engine-free (like `recall` keeps them log-free). The async
engine is cached per running event loop; each decision run gets its own
short-lived session whose lifetime spans the event stream, so the Knowledge
Services read a consistent local snapshot of the canonical store the
connectors populated out of band.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from productagents.agents.context import AgentContext
from productagents.agents.prompts import PromptStore
from productagents.knowledge import build_services
from productagents.knowledge.repositories.sqlmodel.engine import (
    AsyncEngine,
    make_engine,
    make_sessionmaker,
)
from productagents.memory.embedding import HashingEmbedder
from productagents.memory.event_store import EventStore
from productagents.memory.service import LearningService
from productagents.memory.store import DecisionStore

# ponytail: one async engine per running event loop. The engine's
# aiosqlite/asyncpg connections are loop-bound and can't cross an
# asyncio.run() boundary, so the cache is keyed by loop: every fresh CLI
# asyncio.run() gets its own engine; the long-lived sidecar loop reuses one.
# Keys are loop objects (dead loops linger harmlessly for the process life —
# a handful for the CLI, exactly one for the sidecar). Switch to a
# WeakValueDictionary + explicit dispose only if a process ever churns loops.
_engines: dict[object, AsyncEngine] = {}

# ponytail: one process-wide placeholder embedder. Swap for a real model behind
# the Embedder protocol in Phase 7; no caller changes.
_EMBEDDER = HashingEmbedder()


def get_engine() -> AsyncEngine:
    """Build (once per running event loop) and cache the async engine."""
    try:
        loop: object = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    engine = _engines.get(loop)
    if engine is None:
        engine = make_engine()
        _engines[loop] = engine
    return engine


@asynccontextmanager
async def open_agent_context(
    model, *, workspace: str = "default", session_factory=None
) -> AsyncIterator[AgentContext]:
    """Yield an AgentContext bound to one DB session for the duration of a run."""
    factory = session_factory or make_sessionmaker(get_engine())
    async with factory() as session:
        services = build_services(session, workspace)
        learning = LearningService(DecisionStore(session, workspace), _EMBEDDER)
        # Same dir resolution as PromptService.create — live-run nodes must see
        # this workspace's prompt overrides, not the raw PRODUCTAGENTS_PROMPTS_DIR.
        prompts = PromptStore(
            prompts_dir=Path(os.environ.get("PRODUCTAGENTS_PROMPTS_DIR", "prompts"))
            / workspace
        )
        yield AgentContext(
            model=model,
            feedback=services.feedback,
            learning=learning,
            prompts=prompts,
        )


@asynccontextmanager
async def open_event_store(
    *, workspace: str = "default", engine=None
) -> AsyncIterator[EventStore]:
    """Yield an EventStore bound to one DB session (mirrors open_agent_context)."""
    maker = make_sessionmaker(engine or get_engine())
    async with maker() as session:
        yield EventStore(session, workspace)


@asynccontextmanager
async def open_decision_store(
    *, workspace: str = "default", engine=None
) -> AsyncIterator[DecisionStore]:
    """Yield a DecisionStore bound to one DB session (mirrors open_event_store)."""
    maker = make_sessionmaker(engine or get_engine())
    async with maker() as session:
        yield DecisionStore(session, workspace)


def _sessionmaker(engine):
    return make_sessionmaker(engine or get_engine())


def make_recorder(*, workspace: str = "default", engine=None):
    """Async recorder: persist a full DecisionRecord to the memory store."""
    maker = _sessionmaker(engine)

    async def recorder(record) -> None:
        async with maker() as session:
            await LearningService(
                DecisionStore(session, workspace), _EMBEDDER
            ).record_decision(record)

    return recorder


def make_outcome_recorder(*, workspace: str = "default", engine=None):
    """Async outcome recorder: persist a reflected OutcomeRecord."""
    maker = _sessionmaker(engine)

    async def outcome_recorder(outcome) -> None:
        async with maker() as session:
            await LearningService(
                DecisionStore(session, workspace), _EMBEDDER
            ).record_outcome(outcome)

    return outcome_recorder


def make_decision_reader(*, workspace: str = "default", engine=None):
    """Async reader: list persisted decisions (for the reflection picker)."""
    maker = _sessionmaker(engine)

    async def reader() -> list:
        async with maker() as session:
            return await DecisionStore(session, workspace).decisions()

    return reader
