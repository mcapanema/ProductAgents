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
from productagents.agents.context import AgentContext
from productagents.agents.evidence import collect_evidence
from productagents.agents.graph import build_graph
from productagents.core.models import DecisionRecord, HumanDecision, Initiative
from productagents.platform import events as ev
from productagents.platform.bus import EventBus
from productagents.platform.session import Session

logger = logging.getLogger(__name__)

Approver = Callable[[ev.ApprovalRequested], Awaitable[HumanDecision]]
Recorder = Callable[[DecisionRecord], Awaitable[None]]


class DecisionService:
    def __init__(
        self,
        context: AgentContext,
        *,
        recorder: Recorder | None = None,
        human_in_the_loop: bool = False,
    ) -> None:
        self._ctx = context
        self._recorder = recorder
        self._hitl = human_in_the_loop
        self._tasks: set[asyncio.Task] = set()

    def start_session(
        self,
        initiative: Initiative,
        evidence_spec: str,
        *,
        approver: Approver | None = None,
    ) -> tuple[Session, AsyncIterator[ev.Event]]:
        session = Session(id=uuid4().hex, workflow="evaluate_initiative")
        bus = EventBus()
        # subscribe() registers synchronously — no events lost before first iteration
        stream = bus.subscribe()
        task = asyncio.ensure_future(
            self._run(session, bus, initiative, evidence_spec, approver)
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return session, stream

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
            graph = build_graph(self._ctx, human_in_the_loop=self._hitl)
            runner_approver = self._wrap_approver(session, emit, approver)

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
        return await self._ctx.learning.decisions()

    async def get_decision(self, decision_id: str) -> DecisionRecord | None:
        for record in await self._ctx.learning.decisions():
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
