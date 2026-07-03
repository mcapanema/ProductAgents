"""Tests for the ReflectionService platform seam."""

import pytest

from productagents.core.models import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)
from productagents.platform.reflection_service import ReflectionService


def _decision(did="dec-1"):
    return DecisionRecord(
        decision_id=did,
        initiative=Initiative(title="Add SSO", description="Enterprise SSO"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.8,
            rationale="demand",
            expected_outcomes=["enterprise unblock"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


def _outcome(did="dec-1"):
    return OutcomeRecord(
        decision_id=did,
        actual_outcomes=["slow adoption"],
        prediction_accuracy=0.4,
        lessons_learned=["validate demand earlier"],
        reflected_at="2026-06-20T12:00:00+00:00",
    )


def _service(*, decisions=None, outcome=None, recorded=None):
    decisions = decisions if decisions is not None else [_decision()]
    _rec: list = [] if recorded is None else recorded

    async def reader():
        return decisions

    async def reflector(decision, note):
        return outcome or _outcome(decision.decision_id)

    async def recorder(o):
        _rec.append(o)

    return ReflectionService(reflector=reflector, reader=reader, recorder=recorder)


async def test_decisions_lists_from_reader():
    svc = _service(decisions=[_decision("a"), _decision("b")])
    rows = await svc.decisions()
    assert [d.decision_id for d in rows] == ["a", "b"]


async def test_reflect_on_runs_and_persists():
    recorded: list = []
    svc = _service(outcome=_outcome("dec-1"), recorded=recorded)
    out = await svc.reflect_on("dec-1", "shipped, adoption slow")
    assert out.decision_id == "dec-1"
    assert out.prediction_accuracy == 0.4
    assert recorded == [out]  # persisted exactly the returned outcome


async def test_reflect_on_unknown_decision_raises_lookup_error():
    svc = _service(decisions=[_decision("dec-1")], recorded=[])
    with pytest.raises(LookupError):
        await svc.reflect_on("missing", "note")


async def test_for_model_reflector_prompts_are_workspace_scoped(monkeypatch, tmp_path):
    """Regression: for_model used to build its reflector with no `prompts` kwarg,
    so agents/reflection.py fell back to PromptStore() over the shared root and
    silently ignored a workspace's `reflection` prompt override. Mirrors
    test_platform_context.py's test_agent_context_prompts_are_workspace_scoped."""
    override_dir = tmp_path / "team-a" / "reflection"
    override_dir.mkdir(parents=True)
    (override_dir / "0001.txt").write_text("team-a override", encoding="utf-8")
    monkeypatch.setenv("PRODUCTAGENTS_PROMPTS_DIR", str(tmp_path))

    svc = ReflectionService.for_model(None, workspace="team-a")
    prompts = svc._reflect.keywords["prompts"]
    assert prompts.get("reflection") == "team-a override"

    svc_other = ReflectionService.for_model(None, workspace="team-b")
    other_prompts = svc_other._reflect.keywords["prompts"]
    assert other_prompts.active_version("reflection") == 0
