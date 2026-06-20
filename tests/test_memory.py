from productagents.memory import read_decisions, record_decision
from productagents.schemas import (
    AnalystReport,
    DecisionRecord,
    Initiative,
    Recommendation,
)


def _record():
    return DecisionRecord(
        initiative=Initiative(title="Add SSO", description="d"),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["f"],
                signals=["s"],
            )
        ],
        timestamp="2026-06-19T12:00:00+00:00",
    )


def test_record_then_read_round_trips(tmp_path):
    path = tmp_path / "decisions.jsonl"
    record = _record()
    record_decision(record, path=path)
    restored = read_decisions(path=path)
    assert restored == [record]


def test_records_append(tmp_path):
    path = tmp_path / "decisions.jsonl"
    record_decision(_record(), path=path)
    record_decision(_record(), path=path)
    assert len(read_decisions(path=path)) == 2


def test_read_missing_file_returns_empty(tmp_path):
    assert read_decisions(path=tmp_path / "nope.jsonl") == []


def _outcome():
    from productagents.schemas import OutcomeRecord

    return OutcomeRecord(
        decision_id="d1",
        actual_outcomes=["x"],
        prediction_accuracy=0.6,
        lessons_learned=["y"],
        reflected_at="2026-06-20T00:00:00+00:00",
    )


def test_record_then_read_outcomes_round_trips(tmp_path):
    from productagents.memory import read_outcomes, record_outcome

    path = tmp_path / "outcomes.jsonl"
    outcome = _outcome()
    record_outcome(outcome, path=path)
    assert read_outcomes(path=path) == [outcome]


def test_outcomes_append(tmp_path):
    from productagents.memory import read_outcomes, record_outcome

    path = tmp_path / "outcomes.jsonl"
    record_outcome(_outcome(), path=path)
    record_outcome(_outcome(), path=path)
    assert len(read_outcomes(path=path)) == 2


def test_read_missing_outcomes_returns_empty(tmp_path):
    from productagents.memory import read_outcomes

    assert read_outcomes(path=tmp_path / "nope.jsonl") == []
