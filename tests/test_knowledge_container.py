"""build_services wires services to real repositories over one session."""

from productagents.core.models import CustomerFeedback, Initiative, ProductMetric
from productagents.knowledge.container import KnowledgeServices, build_services
from productagents.knowledge.repositories.sqlmodel.canonical_repository import (
    CanonicalRepository,
)
from productagents.knowledge.services.feedback_service import FeedbackQuery
from productagents.knowledge.services.initiative_service import InitiativeQuery
from productagents.knowledge.services.metrics_service import MetricQuery
from tests.storage_fixtures import memory_store


async def test_build_services_returns_the_bundle():
    async with memory_store() as (sessionmaker, _engine), sessionmaker() as session:
        services = build_services(session)
    assert isinstance(services, KnowledgeServices)


async def test_services_read_what_was_written_to_the_store():
    async with memory_store() as (sessionmaker, _engine):
        async with sessionmaker() as write_session:
            await CanonicalRepository(write_session, CustomerFeedback).upsert(
                CustomerFeedback(body="Need SSO", sentiment="negative")
            )
            await CanonicalRepository(write_session, Initiative).upsert(
                Initiative(title="Add SSO", description="Enterprise login")
            )
            await CanonicalRepository(write_session, ProductMetric).upsert(
                ProductMetric(name="WAU", description="Weekly active users")
            )
        async with sessionmaker() as read_session:
            services = build_services(read_session)
            feedback = await services.feedback.search(FeedbackQuery(text="sso"))
            initiatives = await services.initiatives.search(InitiativeQuery(text="sso"))
            metrics = await services.metrics.search(MetricQuery(text="active"))

    assert feedback.total == 1
    assert feedback.items[0].body == "Need SSO"
    assert initiatives.total == 1
    assert metrics.total == 1
