from productagents.agents.human_approval import _final_verdict
from productagents.schemas import GovernanceVerdict


def _advisory(verdict="approve", rationale="strong demand"):
    return GovernanceVerdict(verdict=verdict, rationale=rationale)


def test_final_verdict_records_human_choice_and_advisory():
    final = _final_verdict(
        _advisory(),
        {"verdict": "reject", "rationale": "no capacity this quarter"},
    )
    assert final.verdict == "reject"
    assert final.rationale == "no capacity this quarter"
    assert final.decided_by == "human"
    assert final.advisory_verdict == "approve"
    assert final.advisory_rationale == "strong demand"
    assert final.failed is False


def test_final_verdict_falls_back_to_advisory_rationale_when_note_blank():
    final = _final_verdict(
        _advisory(rationale="resources well spent"),
        {"verdict": "approve", "rationale": ""},
    )
    assert final.verdict == "approve"
    assert final.rationale == "resources well spent"


def test_final_verdict_tolerates_missing_advisory():
    final = _final_verdict(None, {"verdict": "approve", "rationale": "ship it"})
    assert final.verdict == "approve"
    assert final.rationale == "ship it"
    assert final.advisory_verdict is None
    assert final.advisory_rationale is None
    assert final.decided_by == "human"


def test_final_verdict_drops_degraded_advisory_verdict():
    degraded = GovernanceVerdict(
        verdict="error", rationale="LLM call failed", failed=True
    )
    final = _final_verdict(degraded, {"verdict": "approve", "rationale": "looks good"})
    assert final.verdict == "approve"
    assert final.rationale == "looks good"
    assert final.decided_by == "human"
    assert final.advisory_verdict is None
