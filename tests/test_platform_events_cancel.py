from productagents.platform import events as ev
from productagents.platform._event_translation import status_for
from productagents.platform.serialization import deserialize_event, serialize_event


def test_session_cancelled_status_is_cancelled():
    assert status_for(ev.SessionCancelled(session_id="s", seq=3)) == "cancelled"


def test_session_cancelled_round_trips():
    original = ev.SessionCancelled(session_id="s", seq=3)
    etype, payload = serialize_event(original)
    assert etype == "SessionCancelled"
    back = deserialize_event(etype, payload)
    assert isinstance(back, ev.SessionCancelled)
    assert back.session_id == "s"
    assert back.seq == 3
