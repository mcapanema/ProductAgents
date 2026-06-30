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


async def test_hitl_run_requests_approval_and_resumes(decision_inputs_hitl):
    initiative, evidence_spec, context_opener = decision_inputs_hitl
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
