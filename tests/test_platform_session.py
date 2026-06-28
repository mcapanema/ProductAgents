from productagents.platform.session import Session


def test_session_defaults_to_running():
    s = Session(id="abc", workflow="evaluate_initiative")
    assert s.status == "running"
    assert s.created_at is not None


def test_session_status_is_mutable_for_lifecycle_transitions():
    s = Session(id="abc", workflow="evaluate_initiative")
    s.status = "finished"
    assert s.status == "finished"
