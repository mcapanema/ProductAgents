from productagents.core.models import DecisionRecord, Initiative, Recommendation
from productagents.memory.retrieval import (
    cosine,
    select_relevant_lessons,
    semantic_matches,
)


def _decision(decision_id, title, desc):
    return DecisionRecord(
        decision_id=decision_id,
        initiative=Initiative(title=title, description=desc),
        recommendation=Recommendation(
            recommendation="Build it",
            confidence=0.6,
            rationale="rationale",
            expected_outcomes=["o"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


def test_cosine_basic():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine([0.0], [0.0]) == 0.0  # no zero-division


def test_semantic_matches_picks_top_k_above_threshold():
    query = [1.0, 0.0]
    embeddings = {"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [0.9, 0.1]}
    assert semantic_matches(query, embeddings, k=2, threshold=0.1) == {"a", "c"}


def test_also_relevant_surfaces_zero_lexical_overlap_decision():
    # Initiative shares NO tokens with the past decision, so lexical alone finds
    # nothing; passing its id in also_relevant must surface it as derived.
    past = _decision("d1", "Quarterly billing migration", "ledger reconciliation")
    target = Initiative(title="Realtime fraud scoring", description="risk engine")

    assert select_relevant_lessons(target, [past], []) == []
    surfaced = select_relevant_lessons(
        target, [past], [], also_relevant=frozenset({"d1"})
    )
    assert any("Quarterly billing migration" in line for line in surfaced)
