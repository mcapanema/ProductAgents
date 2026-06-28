import dataclasses

import pytest

from productagents.platform import events as ev


def test_event_is_frozen_and_ordered_by_seq():
    a = ev.NodeProgress(session_id="s1", seq=0, node="market", message="thinking")
    b = ev.NodeProgress(session_id="s1", seq=1, node="market", message="done")
    assert a.seq < b.seq
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.seq = 5  # type: ignore


def test_session_started_carries_workflow():
    e = ev.SessionStarted(session_id="s1", seq=0, workflow="evaluate_initiative")
    assert e.workflow == "evaluate_initiative"
    assert isinstance(e, ev.Event)


def test_failed_event_carries_category():
    e = ev.SessionFailed(
        session_id="s1", seq=9, node="strategist", category="rate_limit", message="429"
    )
    assert e.category == "rate_limit"
