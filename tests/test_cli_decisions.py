"""Tests for the `productagents decisions export` CLI command."""

from productagents.app import cli
from productagents.core.models import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)


class _FakeReadService:
    def __init__(self, counts=(2, 1)):
        self._counts = counts
        self.called_with = None

    async def export(self, directory):
        self.called_with = directory
        return self._counts


async def test_decisions_export_reports_counts(tmp_path, capsys):
    service = _FakeReadService((2, 1))
    code = await cli.decisions_export(str(tmp_path), service=service)
    assert code == 0
    assert service.called_with == str(tmp_path)
    out = capsys.readouterr().out
    assert "2 decision(s)" in out
    assert "1 outcome(s)" in out


def _decision_record(did="dec-1", title="Add SSO"):
    return DecisionRecord(
        decision_id=did,
        initiative=Initiative(title=title, description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.8,
            rationale="r",
            expected_outcomes=["x"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


class _FakeDecisions:
    def __init__(self, records=(), outcomes=()):
        self._records = list(records)
        self._outcomes = list(outcomes)

    async def list(self):
        return self._records

    async def get(self, decision_id):
        record = next((d for d in self._records if d.decision_id == decision_id), None)
        if record is None:
            return None, []
        return record, self._outcomes


async def test_decisions_list_prints_summary_lines(capsys):
    service = _FakeDecisions(records=[_decision_record()])
    assert await cli.decisions_list(service=service) == 0
    out = capsys.readouterr().out
    assert "dec-1" in out
    assert "Add SSO" in out
    assert "Build it" in out
    assert "80%" in out


async def test_decisions_list_handles_empty(capsys):
    assert await cli.decisions_list(service=_FakeDecisions()) == 0
    assert "no decisions" in capsys.readouterr().out.lower()


async def test_decisions_show_dumps_record_and_outcomes(capsys):
    outcome = OutcomeRecord(
        decision_id="dec-1",
        actual_outcomes=["slow adoption"],
        prediction_accuracy=0.4,
        lessons_learned=["validate demand earlier"],
        reflected_at="2026-06-20T12:00:00+00:00",
    )
    service = _FakeDecisions(records=[_decision_record()], outcomes=[outcome])
    assert await cli.decisions_show("dec-1", service=service) == 0
    out = capsys.readouterr().out
    assert '"decision_id": "dec-1"' in out
    assert "slow adoption" in out


async def test_decisions_show_unknown_returns_one(capsys):
    assert await cli.decisions_show("nope", service=_FakeDecisions()) == 1
    assert "no such decision" in capsys.readouterr().out
