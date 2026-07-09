"""Tests for DecisionService.start_session.

Happy path: emits SessionStarted … SessionFinished, seq monotone, records once.
HITL path: emits ApprovalRequested + FinalVerdict, approver callback invoked.
"""

import asyncio

from productagents.platform import decision_service as ds
from productagents.platform import events as ev
from productagents.platform.decision_service import DecisionService


async def _collect(stream):
    return [e async for e in stream]


async def test_start_session_streams_platform_events_and_records(decision_inputs):
    """A decision run yields a SessionStarted ... SessionFinished sequence and
    persists exactly one DecisionRecord via the injected recorder."""
    initiative, evidence_spec, context_opener = decision_inputs
    recorded = []

    async def recorder(record):
        recorded.append(record)

    service = DecisionService(context_opener, recorder=recorder)
    session, stream = service.start_session(initiative, evidence_spec)

    received = await _collect(stream)

    assert session.workflow == "evaluate_initiative"
    assert isinstance(received[0], ev.SessionStarted)
    assert isinstance(received[-1], ev.SessionFinished)
    assert [e.seq for e in received] == sorted(e.seq for e in received)
    assert session.status == "finished"
    assert len(recorded) == 1


async def test_recorded_decision_carries_its_session_id(decision_inputs):
    """The persisted DecisionRecord links back to the Session that produced it."""
    initiative, evidence_spec, context_opener = decision_inputs
    recorded = []

    async def recorder(record):
        recorded.append(record)

    service = DecisionService(context_opener, recorder=recorder)
    session, stream = service.start_session(initiative, evidence_spec)
    _ = [e async for e in stream]

    assert len(recorded) == 1
    assert recorded[0].session_id == session.id


async def test_hitl_run_requests_approval_and_resumes(decision_inputs):
    initiative, evidence_spec, context_opener = decision_inputs
    seen_request = {}

    async def approver(request):
        seen_request["verdict"] = request.advisory_verdict
        from productagents.core.models import HumanDecision

        return HumanDecision(verdict="approve", rationale="ok")

    service = DecisionService(context_opener, human_in_the_loop=True)
    _session, stream = service.start_session(
        initiative, evidence_spec, approver=approver
    )

    kinds = [type(e).__name__ async for e in stream]

    assert "ApprovalRequested" in kinds
    assert "FinalVerdict" in kinds
    assert seen_request  # approver was actually invoked


async def test_approver_receives_the_published_seq_not_sentinel(decision_inputs):
    """The approver callback must receive the ApprovalRequested event with the
    real seq (published via emit), not a sentinel seq=-1."""
    initiative, evidence_spec, context_opener = decision_inputs
    approver_received_request = {}
    approval_request_from_stream = None

    async def approver(request):
        approver_received_request["request"] = request
        from productagents.core.models import HumanDecision

        return HumanDecision(verdict="approve", rationale="ok")

    service = DecisionService(context_opener, human_in_the_loop=True)
    _session, stream = service.start_session(
        initiative, evidence_spec, approver=approver
    )

    # Collect all events from stream
    received = await _collect(stream)

    # Find the ApprovalRequested event from the stream
    for e in received:
        if isinstance(e, ev.ApprovalRequested):
            approval_request_from_stream = e
            break

    # Verify the approver received a request
    assert "request" in approver_received_request
    request_to_approver = approver_received_request["request"]

    # Verify the request has the real seq (not -1)
    assert request_to_approver.seq != -1

    # Verify the approver received the same seq as was published in the stream
    assert approval_request_from_stream is not None
    assert request_to_approver.seq == approval_request_from_stream.seq


async def test_for_model_threads_workspace_into_both_openers(monkeypatch):
    """for_model must bind the workspace key into the agent-context opener and
    the event-store opener — otherwise live runs always hit "default"."""
    from productagents.platform import context as ctx_mod

    calls = []

    def fake_agent_context(model, **kwargs):
        calls.append(("agent", kwargs.get("workspace")))
        return "agent-cm"

    def fake_event_store(**kwargs):
        calls.append(("events", kwargs.get("workspace")))
        return "events-cm"

    monkeypatch.setattr(ctx_mod, "open_agent_context", fake_agent_context)
    monkeypatch.setattr(ctx_mod, "open_event_store", fake_event_store)

    service = DecisionService.for_model("model", workspace="team-a")
    assert service._context_opener() == "agent-cm"
    assert service._event_store_opener is not None
    assert service._event_store_opener() == "events-cm"
    assert calls == [("agent", "team-a"), ("events", "team-a")]


async def test_cancel_emits_session_cancelled_and_closes(decision_inputs, monkeypatch):
    from productagents.agents import runner as rn

    started = asyncio.Event()

    async def blocking_run(graph, initiative, evidence, *, approver=None):
        yield rn.ProgressEvent(node="market", message="scanning")
        started.set()
        await asyncio.Event().wait()  # block until the task is cancelled
        yield rn.ProgressEvent(node="never", message="unreached")

    monkeypatch.setattr(ds.rn, "run_decision", blocking_run)

    initiative, evidence_spec, context_opener = decision_inputs
    service = ds.DecisionService(context_opener)
    session, stream = service.start_session(initiative, evidence_spec)

    received = []

    async def consume():
        async for e in stream:
            received.append(e)

    task = asyncio.ensure_future(consume())
    await started.wait()
    assert service.cancel(session.id) is True
    await task

    assert isinstance(received[-1], ev.SessionCancelled)
    assert session.status == "cancelled"
    assert service.cancel(session.id) is False  # run task already gone
