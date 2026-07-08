"""Golden guard: the nested payload shapes the desktop GUI casts to must match
what serialize_event() emits. The expected key sets mirror the TypeScript
interfaces in desktop/src/ipc/events.ts — if a canonical-model field is renamed
or dropped, this test fails and names the TS file to update in lockstep.
"""

from productagents.core.models import AnalystReport, Recommendation
from productagents.platform import events as ev
from productagents.platform.serialization import serialize_event

# ---- expected key sets, copied from desktop/src/ipc/events.ts ----
# AnalystReportPayload
_REPORT_KEYS = {"analyst", "role", "findings", "signals", "failed"}
# RecommendationPayload
_REC_KEYS = {"recommendation", "confidence", "rationale", "expected_outcomes", "failed"}
# JudgedPayload
_JUDGED_KEYS = {
    "passed",
    "evidence_grounding_score",
    "rationale_coherence_score",
    "critique",
    "attempt",
}
# RiskAssessedPayload
_RISK_KEYS = {"reviewer", "role", "level", "rationale"}

_TS_REF = "desktop/src/ipc/events.ts"


def _payload(event) -> dict:
    _type, payload = serialize_event(event)
    return payload


def test_analyst_report_payload_shape():
    report = AnalystReport(
        analyst="market", role="market analyst", findings=["f"], signals=["s"]
    )
    payload = _payload(
        ev.AnalystCompleted(session_id="s", seq=1, node="market", report=report)
    )
    assert set(payload["report"]) == _REPORT_KEYS, (
        f"AnalystReportPayload drifted — update {_TS_REF}"
    )


def test_recommendation_payload_shape():
    rec = Recommendation(
        recommendation="Build it",
        confidence=0.7,
        rationale="r",
        expected_outcomes=["o"],
    )
    payload = _payload(ev.Recommended(session_id="s", seq=1, recommendation=rec))
    assert set(payload["recommendation"]) == _REC_KEYS, (
        f"RecommendationPayload drifted — update {_TS_REF}"
    )


def test_judged_payload_shape():
    payload = _payload(
        ev.Judged(
            session_id="s",
            seq=1,
            passed=True,
            evidence_grounding_score=0.9,
            rationale_coherence_score=0.8,
            critique="c",
            attempt=1,
        )
    )
    assert set(payload) >= _JUDGED_KEYS, f"JudgedPayload drifted — update {_TS_REF}"


def test_risk_assessed_payload_shape():
    payload = _payload(
        ev.RiskAssessed(
            session_id="s", seq=1, reviewer="r", role="sec", level="low", rationale="ok"
        )
    )
    assert set(payload) >= _RISK_KEYS, f"RiskAssessedPayload drifted — update {_TS_REF}"
