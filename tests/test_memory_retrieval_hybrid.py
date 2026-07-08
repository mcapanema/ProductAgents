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


def test_semantic_matches_default_threshold_excludes_weak_similarity():
    import productagents.memory.retrieval as retrieval

    assert retrieval._SEMANTIC_THRESHOLD == 0.35  # documents the chosen bar
    query = [1.0, 0.0]
    # cosine(query, weak) == 0.196..., between the old 0.1 and the new default.
    weak = [0.2, 0.98]
    strong = [0.95, 0.31]  # cosine == 0.95
    out = retrieval.semantic_matches(query, {"weak": weak, "strong": strong})
    assert out == {"strong"}  # weak match dropped at the default threshold


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
