"""Sample canonical models + an in-memory store, shared by storage tests."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from productagents.core.models import (
    CanonicalModel,
    CustomerFeedback,
    Feature,
    Incident,
    Initiative,
    KeyResult,
    MetricSnapshot,
    Objective,
    ProductMetric,
    RoadmapItem,
    SupportTicket,
    UserSegment,
)
from productagents.knowledge.repositories.sqlmodel.engine import (
    create_all,
    make_engine,
    make_sessionmaker,
)


def sample_models() -> list[CanonicalModel]:
    """One instance of each canonical model type, all with required fields set."""
    return [
        Initiative(title="Add SSO", description="Enterprise login"),
        Feature(name="SAML support"),
        RoadmapItem(title="SSO GA"),
        CustomerFeedback(body="Please add SSO"),
        SupportTicket(subject="SSO broken"),
        UserSegment(name="Enterprise"),
        Incident(title="Login outage"),
        Objective(title="Win enterprise"),
        KeyResult(description="10 enterprise logos"),
        ProductMetric(name="WAU"),
        MetricSnapshot(value=1234.0),
    ]


@asynccontextmanager
async def memory_store() -> AsyncIterator:
    """Yield a (sessionmaker, engine) over a fresh in-memory canonical store."""
    engine = make_engine("sqlite+aiosqlite://")
    await create_all(engine)
    try:
        yield make_sessionmaker(engine), engine
    finally:
        await engine.dispose()
