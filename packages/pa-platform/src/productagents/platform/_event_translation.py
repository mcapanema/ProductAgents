"""Pure translation from runner results to platform events. No I/O, no session state."""

import logging
from collections.abc import Callable

from productagents.agents import runner as rn
from productagents.platform import events as ev

logger = logging.getLogger(__name__)


def status_for(event: ev.Event) -> str | None:
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


def translate(session, r) -> Callable[[int], ev.Event] | None:
    sid = session.id
    match r:
        case rn.ProgressEvent(node=n, message=m):
            return lambda s: ev.NodeProgress(session_id=sid, seq=s, node=n, message=m)
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
            return lambda s: ev.Recommended(session_id=sid, seq=s, recommendation=rec)
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
