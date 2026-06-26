"""The graph↔store boundary: open a per-run session, wire services, run.

Keeps graph nodes engine-free (like `recall` keeps them log-free). The engine is
process-wide; each decision run gets its own short-lived session whose lifetime
spans the event stream, so the Knowledge Services read a consistent local
snapshot of the canonical store the connectors populated out of band.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from productagents.agents.context import AgentContext
from productagents.agents.graph import build_graph
from productagents.agents.runner import run_decision
from productagents.knowledge import build_services
from productagents.knowledge.repositories.sqlmodel.engine import (
    make_engine,
    make_sessionmaker,
)

# ponytail: one process-wide engine over the local SQLite file. Pool/replace per
# request if this ever serves concurrent decision runs.
_engine = None


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
        yield AgentContext(model=model, feedback=services.feedback)


def make_decision_runner(
    model, *, context_opener=open_agent_context, human_in_the_loop=True
):
    """Build a runner with `run_decision`'s call signature.

    Each call opens a fresh AgentContext + graph inside one session scope, so the
    `self._runner(...)` seam the TUI (and its tests) use is unchanged.
    """

    async def runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        # ponytail: session stays open across human_approval interrupt; fine for
        # local SQLite, becomes a held connection under Postgres concurrency —
        # upgrade path: open a fresh session after the interrupt resumes.
        async with context_opener(model) as ctx:
            graph = build_graph(ctx, human_in_the_loop=human_in_the_loop)
            async for event in run_decision(
                graph,
                initiative,
                evidence,
                approver=approver,
            ):
                yield event

    return runner
