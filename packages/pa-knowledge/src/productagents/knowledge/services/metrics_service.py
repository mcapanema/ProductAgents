"""Product-metric definition questions."""

from productagents.core.models import ProductMetric
from productagents.knowledge.services._query import Query
from productagents.knowledge.services._service import CanonicalQueryService


class MetricQuery(Query[ProductMetric]):
    """Filter metric definitions by free text (name + description)."""

    text: str | None = None

    def matches(self, model: ProductMetric) -> bool:
        if self.text is not None:
            haystack = f"{model.name} {model.description}".lower()
            if self.text.lower() not in haystack:
                return False
        return True


class MetricsService(CanonicalQueryService[ProductMetric]):
    """The platform's metrics API: ``search(MetricQuery)`` + ``get``."""
