"""Discovery context: what users and operations are telling us."""

from datetime import datetime

from pydantic import Field

from productagents.core.enums import (
    IncidentStatus,
    Priority,
    Sentiment,
    Severity,
    TicketStatus,
)
from productagents.core.ids import (
    FeedbackId,
    IncidentId,
    SupportTicketId,
    UserSegmentId,
    new_id,
)
from productagents.core.models._base import CanonicalModel


class CustomerFeedback(CanonicalModel):
    """A single piece of qualitative customer feedback."""

    id: FeedbackId = Field(default_factory=lambda: FeedbackId(new_id()))
    body: str
    sentiment: Sentiment | None = None
    segment: str | None = None
    author: str | None = None
    submitted_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class SupportTicket(CanonicalModel):
    """A support request raised by a customer."""

    id: SupportTicketId = Field(default_factory=lambda: SupportTicketId(new_id()))
    subject: str
    body: str = ""
    status: TicketStatus = "open"
    priority: Priority = "medium"
    requester: str | None = None
    opened_at: datetime | None = None
    resolved_at: datetime | None = None


class UserSegment(CanonicalModel):
    """A cohort of users the product reasons about."""

    id: UserSegmentId = Field(default_factory=lambda: UserSegmentId(new_id()))
    name: str
    description: str = ""
    size: int | None = None


class Incident(CanonicalModel):
    """A production incident affecting users."""

    id: IncidentId = Field(default_factory=lambda: IncidentId(new_id()))
    title: str
    description: str = ""
    severity: Severity = "sev3"
    status: IncidentStatus = "investigating"
    started_at: datetime | None = None
    resolved_at: datetime | None = None
