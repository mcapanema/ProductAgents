from productagents.agents import stream_events as ev
from productagents.core.models import DebateTurn


def test_emit_status_shape():
    assert ev.emit_status("debate", "round 1") == {
        "node": "debate",
        "status": "round 1",
    }


def test_emit_error_shape():
    assert ev.emit_error("risk", "boom") == {"node": "risk", "error": "boom"}


def test_emit_fatal_marks_fatal_and_category():
    chunk = ev.emit_fatal("customer_research", "rate limited", "rate_limit")
    assert chunk == {
        "node": "customer_research",
        "error": "rate limited",
        "fatal": True,
        "category": "rate_limit",
    }


def test_emit_payload_dumps_model_under_the_given_key():
    turn = DebateTurn(round=1, side="advocate", argument="ship it")
    chunk = ev.emit_payload("debate", ev.TURN, turn)
    assert chunk == {"node": "debate", "turn": turn.model_dump()}


def test_key_constants_match_the_frozen_wire_format():
    # These string values are the wire contract; renaming them breaks the runner
    # and the hand-built chunks in test_runner.py.
    assert (ev.NODE, ev.STATUS, ev.ERROR, ev.FATAL, ev.CATEGORY) == (
        "node",
        "status",
        "error",
        "fatal",
        "category",
    )
    assert (ev.TURN, ev.ASSESSMENT, ev.JUDGMENT, ev.VERDICT, ev.FINAL_VERDICT) == (
        "turn",
        "assessment",
        "judgment",
        "verdict",
        "final_verdict",
    )
