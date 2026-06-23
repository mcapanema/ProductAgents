from productagents.core.models.discovery import (
    CustomerFeedback,
    Incident,
    SupportTicket,
    UserSegment,
)


def test_customer_feedback_minimal_and_round_trip():
    fb = CustomerFeedback(body="Login is too slow", sentiment="negative")
    assert fb.body == "Login is too slow"
    assert fb.sentiment == "negative"
    assert fb.source.connector == "manual"  # inherited default
    assert CustomerFeedback.model_validate_json(fb.model_dump_json()) == fb


def test_support_ticket_defaults():
    t = SupportTicket(subject="Cannot reset password")
    assert t.status == "open"
    assert t.priority == "medium"


def test_user_segment_and_incident_construct():
    seg = UserSegment(name="Enterprise", size=120)
    assert seg.size == 120
    inc = Incident(title="API outage", severity="sev1")
    assert inc.severity == "sev1"
    assert inc.status == "investigating"
