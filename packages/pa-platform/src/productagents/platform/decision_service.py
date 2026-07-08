"""DecisionService — run the evaluate-initiative pipeline as a streamed session.

Wraps the agents graph + runner, translates runner events into the platform's
stable event vocabulary, owns decision recording, and exposes the result as an
``EventBus`` stream. Presentation calls ``start_session`` and renders events.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

from productagents.agents import runner as rn
from productagents.agents.evidence import collect_evidence
from productagents.agents.graph import build_graph
from productagents.core.models import DecisionRecord, HumanDecision, Initiative
from productagents.platform import events as ev
from productagents.platform._event_translation import status_for, translate
from productagents.platform.bus import EventBus
from productagents.platform.serialization import serialize_event
from productagents.platform.session import Session

logger = logging.getLogger(__name__)

Approver = Callable[[ev.ApprovalRequested], Awaitable[HumanDecision]]
Recorder = Callable[[DecisionRecord], Awaitable[None]]


class DecisionService:
    def __init__(
        self,
        context_opener,
        *,
        recorder: Recorder | None = None,
        human_in_the_loop: bool = False,
        event_store_opener=None,
    ) -> None:
        # context_opener: Callable[[], AbstractAsyncContextManager[AgentContext]]
        # event_store_opener: Callable[[], AbstractAsyncContextManager[EventStore]]|None
        self._context_opener = context_opener
        self._recorder = recorder
        self._hitl = human_in_the_loop
        self._event_store_opener = event_store_opener
        self._tasks: set[asyncio.Task] = set()
        self._runs: dict[str, asyncio.Task] = {}

    @classmethod
    def for_model(
        cls,
        model,
        *,
        recorder: Recorder | None = None,
        human_in_the_loop: bool = False,
        persist_events: bool = True,
        workspace: str = "default",
    ) -> DecisionService:
        from functools import partial

        from productagents.platform.context import open_agent_context, open_event_store

        return cls(
            lambda: open_agent_context(model, workspace=workspace),
            recorder=recorder,
            human_in_the_loop=human_in_the_loop,
            event_store_opener=(
                partial(open_event_store, workspace=workspace)
                if persist_events
                else None
            ),
        )

    def _spawn(self, coro) -> asyncio.Task:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def start_session(
        self,
        initiative: Initiative,
        evidence_spec: str,
        *,
        approver: Approver | None = None,
    ) -> tuple[Session, AsyncIterator[ev.Event]]:
        session = Session(id=uuid4().hex, workflow="evaluate_initiative")
        bus = EventBus()
        # subscribe() registers synchronously — no events lost before iteration.
        stream = bus.subscribe()  # the caller's (UI) stream
        if self._event_store_opener is not None:
            # The Event Store is just another subscriber on the same bus. Pass the
            # (now-narrowed non-None) opener in so _persist needs no None check.
            opener = self._event_store_opener
            self._spawn(self._persist(session, bus.subscribe(), opener))
        run_task = self._spawn(
            self._run(session, bus, initiative, evidence_spec, approver)
        )
        self._runs[session.id] = run_task
        run_task.add_done_callback(lambda _t, sid=session.id: self._runs.pop(sid, None))
        return session, stream

    def cancel(self, session_id: str) -> bool:
        """Cancel a live run task. Cooperative: the run's _run coroutine catches
        CancelledError, emits SessionCancelled, and closes the bus."""
        task = self._runs.get(session_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def _persist(
        self, session: Session, stream: AsyncIterator[ev.Event], opener
    ) -> None:
        """Drain the bus into the Event Store. Never let a storage failure abort a
        run — the DB stays the system of record; this is an execution log."""
        try:
            async with opener() as store:
                await store.start_session(
                    session.id,
                    session.workflow,
                    "running",
                    session.created_at.isoformat(),
                )
                async for event in stream:
                    event_type, payload = serialize_event(event)
                    await store.append(
                        session.id,
                        event.seq,
                        event_type,
                        event.ts.isoformat(),
                        payload,
                    )
                    status = status_for(event)
                    if status is not None:
                        await store.update_status(session.id, status)
        except Exception:
            logger.exception("event persistence for session %s failed", session.id)

    async def _run(
        self,
        session: Session,
        bus: EventBus,
        initiative: Initiative,
        evidence_spec: str,
        approver: Approver | None,
    ) -> None:
        seq = 0

        def emit(make: Callable[[int], ev.Event]) -> None:
            nonlocal seq
            bus.publish(make(seq))
            seq += 1

        try:
            emit(
                lambda s: ev.SessionStarted(
                    session_id=session.id, seq=s, workflow=session.workflow
                )
            )
            evidence = collect_evidence(evidence_spec)
            runner_approver = self._wrap_approver(session, emit, approver)

            # Open a fresh context per run; session stays open across the full
            # event stream including any human-approval interrupt.
            async with self._context_opener() as ctx:
                graph = build_graph(ctx, human_in_the_loop=self._hitl)

                async for r in rn.run_decision(
                    graph, initiative, evidence, approver=runner_approver
                ):
                    translated = translate(session, r)
                    if translated is not None:
                        emit(translated)
                    if isinstance(r, rn.RunAbortedEvent):
                        session.status = "failed"
                        return
                    if isinstance(r, rn.FinishedEvent):
                        await self._record(session, initiative, evidence, r)
                        session.status = "finished"
        except asyncio.CancelledError:
            session.status = "cancelled"
            emit(lambda s: ev.SessionCancelled(session_id=session.id, seq=s))
            raise
        except Exception:
            logger.exception("decision session %s crashed", session.id)
            session.status = "failed"
            emit(
                lambda s: ev.SessionFailed(
                    session_id=session.id,
                    seq=s,
                    node="session",
                    category="internal",
                    message="internal error — see logs",
                )
            )
        finally:
            bus.close()

    def _wrap_approver(self, session, emit, approver):
        if approver is None:
            return None

        async def runner_approver(advisory):
            session.status = "awaiting_approval"
            advisory_verdict = advisory.verdict if advisory else "approve"
            advisory_rationale = advisory.rationale if advisory else ""
            request_box: list[ev.ApprovalRequested] = []

            def _make(s: int) -> ev.ApprovalRequested:
                request = ev.ApprovalRequested(
                    session_id=session.id,
                    seq=s,
                    advisory_verdict=advisory_verdict,
                    advisory_rationale=advisory_rationale,
                )
                request_box.append(request)  # the published instance, real seq
                return request

            emit(_make)
            decision = await approver(request_box[0])
            session.status = "running"
            return decision

        return runner_approver

    async def _record(self, session, initiative, evidence, finished) -> None:
        if self._recorder is None:
            return
        if finished.recommendation is None or finished.recommendation.failed:
            return  # degraded run — don't persist a failed decision
        record = self._build_record(session, initiative, evidence, finished)
        await self._recorder(record)

    async def list_decisions(self) -> list[DecisionRecord]:
        async with self._context_opener() as ctx:
            return await ctx.learning.decisions()

    async def get_decision(self, decision_id: str) -> DecisionRecord | None:
        async with self._context_opener() as ctx:
            for record in await ctx.learning.decisions():
                if record.decision_id == decision_id:
                    return record
        return None

    def _build_record(self, session, initiative, evidence, finished) -> DecisionRecord:
        return DecisionRecord(
            session_id=session.id,
            initiative=initiative,
            recommendation=finished.recommendation,
            reports=finished.reports,
            debate=finished.debate,
            risks=finished.risks,
            governance=finished.governance,
            judgment=finished.judgment,
            prior_lessons=finished.prior_lessons,
            evidence_sources=evidence.sources,
            timestamp=datetime.now(UTC).isoformat(),
        )
