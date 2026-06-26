"""Customer-feedback questions, expressed as product concepts not tables."""

from productagents.core.enums import Sentiment
from productagents.core.models import CustomerFeedback
from productagents.knowledge.services._query import Query
from productagents.knowledge.services._service import CanonicalQueryService


class FeedbackQuery(Query[CustomerFeedback]):
    """Filter customer feedback by segment, sentiment, and free text."""

    text: str | None = None
    sentiment: Sentiment | None = None
    segment: str | None = None

    def matches(self, model: CustomerFeedback) -> bool:
        if self.sentiment is not None and model.sentiment != self.sentiment:
            return False
        if self.segment is not None and model.segment != self.segment:
            return False
        if self.text is not None:
            return self.text.lower() in model.body.lower()
        return True


class FeedbackService(CanonicalQueryService[CustomerFeedback]):
    """The platform's customer-feedback API: ``search(FeedbackQuery)`` + ``get``."""
