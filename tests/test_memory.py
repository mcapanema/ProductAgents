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
