from productagents.memory import (
    read_decisions,
    read_outcomes,
    record_decision,
    record_outcome,
)
from productagents.schemas import (
    AnalystReport,
    DecisionRecord,
    Initiative,
    OutcomeRecord,
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


def test_read_skips_invalid_records(tmp_path):
    # A legacy record whose governance.advisory_verdict holds the now-invalid
    # "error" sentinel must be skipped, not crash the whole read. The valid
    # record written after it is still returned.
    path = tmp_path / "decisions.jsonl"
    bad_line = (
        '{"decision_id":"legacy","initiative":{"title":"Add SSO","description":"d"},'
        '"recommendation":{"recommendation":"x","confidence":0.0,"rationale":"r",'
        '"expected_outcomes":[]},"reports":[],'
        '"governance":{"verdict":"request_analysis","rationale":"r",'
        '"decided_by":"human","advisory_verdict":"error"},'
        '"timestamp":"2026-06-20T00:00:00+00:00"}'
    )
    path.write_text(bad_line + "\n", encoding="utf-8")
    good = _record()
    record_decision(good, path=path)

    assert read_decisions(path=path) == [good]


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
    path = tmp_path / "outcomes.jsonl"
    outcome = _outcome()
    record_outcome(outcome, path=path)
    assert read_outcomes(path=path) == [outcome]


def test_outcomes_append(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    record_outcome(_outcome(), path=path)
    record_outcome(_outcome(), path=path)
    assert len(read_outcomes(path=path)) == 2


def test_read_missing_outcomes_returns_empty(tmp_path):
    assert read_outcomes(path=tmp_path / "nope.jsonl") == []


def test_read_outcomes_skips_invalid_records(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    # prediction_accuracy out of [0, 1] is invalid and must be skipped.
    path.write_text(
        '{"decision_id":"bad","actual_outcomes":[],"prediction_accuracy":5.0,'
        '"lessons_learned":[],"reflected_at":"2026-06-20T00:00:00+00:00"}\n',
        encoding="utf-8",
    )
    good = _outcome()
    record_outcome(good, path=path)

    assert read_outcomes(path=path) == [good]


def _decision(decision_id, title, description="d"):
    from productagents.schemas import DecisionRecord, Initiative, Recommendation

    return DecisionRecord(
        decision_id=decision_id,
        initiative=Initiative(title=title, description=description),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.7,
            rationale="r",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


def _outcome_for(decision_id, lessons, *, accuracy=0.6, failed=False):
    from productagents.schemas import OutcomeRecord

    return OutcomeRecord(
        decision_id=decision_id,
        actual_outcomes=["x"],
        prediction_accuracy=accuracy,
        lessons_learned=lessons,
        reflected_at="2026-06-20T00:00:00+00:00",
        failed=failed,
    )


def test_selects_lessons_from_matching_decision():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [
        _decision("d1", "Add enterprise SSO login"),
        _decision("d2", "Redesign the billing dashboard"),
    ]
    outcomes = [
        _outcome_for("d1", ["SSO took two quarters, not one"], accuracy=0.5),
        _outcome_for("d2", ["billing rewrite slipped"]),
    ]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO support")

    lessons = select_relevant_lessons(initiative, decisions, outcomes)

    assert any("SSO took two quarters" in line for line in lessons)
    assert all("billing rewrite" not in line for line in lessons)
    # provenance: the source initiative title and accuracy are included
    assert any("Add enterprise SSO login" in line for line in lessons)
    assert any("50%" in line for line in lessons)


def test_ignores_decisions_without_an_outcome():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [_decision("d1", "Add enterprise SSO login")]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    assert select_relevant_lessons(initiative, decisions, outcomes=[]) == []


def test_ignores_failed_or_empty_outcomes():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [
        _decision("d1", "Add enterprise SSO login"),
        _decision("d2", "Add SSO provisioning"),
    ]
    outcomes = [
        _outcome_for("d1", ["this lesson is from a failed reflection"], failed=True),
        _outcome_for("d2", []),  # no lessons captured
    ]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    assert select_relevant_lessons(initiative, decisions, outcomes) == []


def test_returns_empty_when_no_token_overlap():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [_decision("d1", "Migrate the data warehouse")]
    outcomes = [_outcome_for("d1", ["warehouse migration was risky"])]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    assert select_relevant_lessons(initiative, decisions, outcomes) == []


def test_respects_limit():
    from productagents.memory import select_relevant_lessons
    from productagents.schemas import Initiative

    decisions = [_decision(f"d{i}", "Add SSO login support") for i in range(5)]
    outcomes = [_outcome_for(f"d{i}", [f"lesson {i}"]) for i in range(5)]
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    lessons = select_relevant_lessons(initiative, decisions, outcomes, limit=2)
    assert len(lessons) == 2


# Brief: Step 1 outcome log parity tests


def _outcome_brief():
    return OutcomeRecord(
        decision_id="abc123",
        actual_outcomes=["shipped late"],
        prediction_accuracy=0.6,
        lessons_learned=["scope smaller"],
        reflected_at="2026-06-20T12:00:00+00:00",
    )


def test_outcome_record_then_read_round_trips(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    outcome = _outcome_brief()
    record_outcome(outcome, path=path)
    assert read_outcomes(path=path) == [outcome]


def test_read_outcomes_missing_file_returns_empty(tmp_path):
    assert read_outcomes(path=tmp_path / "nope.jsonl") == []


def test_read_outcomes_skips_blank_and_invalid_lines(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    record_outcome(_outcome_brief(), path=path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n")  # blank line skipped
        handle.write("{not valid json}\n")  # invalid line skipped
    assert read_outcomes(path=path) == [_outcome_brief()]
