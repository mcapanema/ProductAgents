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
from productagents.platform.bus import EventBus
from productagents.platform.serialization import serialize_event
from productagents.platform.session import Session

logger = logging.getLogger(__name__)

Approver = Callable[[ev.ApprovalRequested], Awaitable[HumanDecision]]
Recorder = Callable[[DecisionRecord], Awaitable[None]]


def _status_for(event: ev.Event) -> str | None:
    """The session status a terminal/approval event implies (None = no change)."""
    match event:
        case ev.ApprovalRequested():
            return "awaiting_approval"
        case ev.SessionFinished():
            return "finished"
        case ev.SessionFailed():
            return "failed"
        case _:
            return None


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

    @classmethod
    def for_model(
        cls,
        model,
        *,
        recorder: Recorder | None = None,
        human_in_the_loop: bool = False,
        persist_events: bool = True,
    ) -> DecisionService:
        from productagents.platform.context import open_agent_context, open_event_store

        return cls(
            lambda: open_agent_context(model),
            recorder=recorder,
            human_in_the_loop=human_in_the_loop,
            event_store_opener=open_event_store if persist_events else None,
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
            # The Event Store is just another subscriber on the same bus.
            self._spawn(self._persist(session, bus.subscribe()))
        self._spawn(self._run(session, bus, initiative, evidence_spec, approver))
        return session, stream

    async def _persist(self, session: Session, stream: AsyncIterator[ev.Event]) -> None:
        """Drain the bus into the Event Store. Never let a storage failure abort a
        run — the DB stays the system of record; this is an execution log."""
        assert self._event_store_opener is not None  # only spawned when opener is set
        try:
            async with self._event_store_opener() as store:
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
                    status = _status_for(event)
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
                    translated = self._translate(session, r)
                    if translated is not None:
                        emit(translated)
                    if isinstance(r, rn.RunAbortedEvent):
                        session.status = "failed"
                        return
                    if isinstance(r, rn.FinishedEvent):
                        await self._record(session, initiative, evidence, r)
                        session.status = "finished"
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
            emit(
                lambda s: ev.ApprovalRequested(
                    session_id=session.id,
                    seq=s,
                    advisory_verdict=advisory_verdict,
                    advisory_rationale=advisory_rationale,
                )
            )
            decision = await approver(
                ev.ApprovalRequested(
                    session_id=session.id,
                    seq=-1,
                    advisory_verdict=advisory_verdict,
                    advisory_rationale=advisory_rationale,
                )
            )
            session.status = "running"
            return decision

        return runner_approver

    def _translate(self, session, r) -> Callable[[int], ev.Event] | None:
        sid = session.id
        match r:
            case rn.ProgressEvent(node=n, message=m):
                return lambda s: ev.NodeProgress(
                    session_id=sid, seq=s, node=n, message=m
                )
            case rn.NodeCompleteEvent(node=n, report=rep):
                return lambda s: ev.AnalystCompleted(
                    session_id=sid, seq=s, node=n, report=rep
                )
            case rn.DebateTurnEvent(round=rd, side=sd, argument=a):
                return lambda s: ev.DebateTurnEmitted(
                    session_id=sid, seq=s, round=rd, side=sd, argument=a
                )
            case rn.RiskAssessmentEvent(reviewer=rv, role=ro, level=lv, rationale=ra):
                return lambda s: ev.RiskAssessed(
                    session_id=sid, seq=s, reviewer=rv, role=ro, level=lv, rationale=ra
                )
            case rn.RecommendationEvent(recommendation=rec):
                return lambda s: ev.Recommended(
                    session_id=sid, seq=s, recommendation=rec
                )
            case rn.JudgmentEvent() as j:
                return lambda s: ev.Judged(
                    session_id=sid,
                    seq=s,
                    passed=j.passed,
                    evidence_grounding_score=j.evidence_grounding_score,
                    rationale_coherence_score=j.rationale_coherence_score,
                    critique=j.critique,
                    attempt=j.attempt,
                )
            case rn.GovernanceVerdictEvent(verdict=v, rationale=ra):
                return lambda s: ev.GovernanceAdvised(
                    session_id=sid, seq=s, verdict=v, rationale=ra
                )
            case rn.RecallEvent(lessons=ls):
                return lambda s: ev.LessonsRecalled(session_id=sid, seq=s, lessons=ls)
            case rn.NodeErrorEvent(node=n, message=m):
                return lambda s: ev.NodeFailed(session_id=sid, seq=s, node=n, message=m)
            case rn.RunAbortedEvent(node=n, category=c, message=m):
                return lambda s: ev.SessionFailed(
                    session_id=sid, seq=s, node=n, category=c, message=m
                )
            case rn.FinalVerdictEvent(verdict=v, rationale=ra, decided_by=db):
                return lambda s: ev.FinalVerdict(
                    session_id=sid, seq=s, verdict=v, rationale=ra, decided_by=db
                )
            case rn.FinishedEvent() as f:
                return lambda s: ev.SessionFinished(
                    session_id=sid,
                    seq=s,
                    recommendation=f.recommendation,
                    reports=f.reports,
                    debate=f.debate,
                    risks=f.risks,
                    governance=f.governance,
                    prior_lessons=f.prior_lessons,
                    judgment=f.judgment,
                )
            case _:
                logger.warning("decision_service: untranslated runner event %r", r)
                return None

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
        # Ported field-for-field from tui/app.py ProductAgentsApp._record.
        # Task 9 will delete that copy; keep these fields in sync until then.
        return DecisionRecord(
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
