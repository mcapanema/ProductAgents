"""Initiative questions — the spine every decision run hangs off."""

from productagents.core.enums import InitiativeStatus
from productagents.core.models import Initiative
from productagents.knowledge.services._query import Query
from productagents.knowledge.services._service import CanonicalQueryService


class InitiativeQuery(Query[Initiative]):
    """Filter initiatives by status and free text (title + description)."""

    text: str | None = None
    status: InitiativeStatus | None = None

    def matches(self, model: Initiative) -> bool:
        if self.status is not None and model.status != self.status:
            return False
        if self.text is not None:
            haystack = f"{model.title} {model.description}".lower()
            if self.text.lower() not in haystack:
                return False
        return True


class InitiativeService(CanonicalQueryService[Initiative]):
    """The platform's initiative API: ``search(InitiativeQuery)`` + ``get``."""
