"""FeedbackService searches customer feedback by sentiment, segment, and text."""

from productagents.core.models import CustomerFeedback
from productagents.knowledge.services.feedback_service import (
    FeedbackQuery,
    FeedbackService,
)
from tests.knowledge_fakes import FakeRepository


def _corpus() -> list[CustomerFeedback]:
    return [
        CustomerFeedback(
            body="Love the SSO flow", sentiment="positive", segment="enterprise"
        ),
        CustomerFeedback(
            body="SSO is broken on login", sentiment="negative", segment="enterprise"
        ),
        CustomerFeedback(
            body="Pricing is too high", sentiment="negative", segment="smb"
        ),
    ]


async def test_search_filters_by_sentiment_and_text():
    svc = FeedbackService(FakeRepository(_corpus()))
    page = await svc.search(FeedbackQuery(text="sso", sentiment="negative"))
    assert [f.body for f in page.items] == ["SSO is broken on login"]
    assert page.total == 1


async def test_search_filters_by_segment():
    svc = FeedbackService(FakeRepository(_corpus()))
    page = await svc.search(FeedbackQuery(segment="smb"))
    assert [f.body for f in page.items] == ["Pricing is too high"]


async def test_empty_query_returns_everything():
    svc = FeedbackService(FakeRepository(_corpus()))
    page = await svc.search(FeedbackQuery())
    assert page.total == 3


async def test_get_is_inherited():
    corpus = _corpus()
    svc = FeedbackService(FakeRepository(corpus))
    assert await svc.get(str(corpus[0].id)) == corpus[0]
