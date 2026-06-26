import math
import re

from productagents.core.models import DecisionRecord, Initiative, OutcomeRecord

# Short, ubiquitous words carry no signal for matching past initiatives.
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "for",
        "to",
        "of",
        "in",
        "on",
        "with",
        "is",
        "are",
        "be",
        "this",
        "that",
        "it",
        "as",
        "by",
        "at",
        "from",
        "our",
        "we",
        "add",
        "new",
        "support",
    }
)


def _tokens(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) > 2 and word not in _STOPWORDS
    }


def _derived_lesson(decision: DecisionRecord) -> str:
    """A prediction-style lesson synthesized from a past decision with no
    validated outcome yet.

    Marked "not yet validated" so the strategist weighs it as a prior
    *prediction* (what we decided and why), not an observed result.
    """
    rec = decision.recommendation
    return (
        f'From "{decision.initiative.title}" '
        f'(decided "{rec.recommendation}", {rec.confidence:.0%} confidence, '
        f"not yet validated): {rec.rationale}"
    )


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity; 0.0 when either vector is empty or zero-length."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def semantic_matches(
    query: list[float],
    embeddings: dict[str, list[float]],
    *,
    k: int = 5,
    threshold: float = 0.1,
) -> set[str]:
    """Decision ids whose embedding is closest to ``query`` (top-k over threshold).

    ponytail: linear scan + Python cosine — honest at local-first scale. Upgrade
    path is a vector index (sqlite-vec / pgvector) behind this same signature.
    """
    scored = [
        (cosine(query, vec), decision_id) for decision_id, vec in embeddings.items()
    ]
    scored = [
        (score, decision_id) for score, decision_id in scored if score >= threshold
    ]
    scored.sort(reverse=True)
    return {decision_id for _, decision_id in scored[:k]}


def select_relevant_lessons(
    initiative: Initiative,
    decisions: list[DecisionRecord],
    outcomes: list[OutcomeRecord],
    *,
    limit: int = 3,
    also_relevant: frozenset[str] = frozenset(),
) -> list[str]:
    """Return formatted lessons from the past decisions most similar to `initiative`.

    Two kinds of lessons, validated first:
    - **Outcome-backed**: from a prior decision's reflected `OutcomeRecord`
      (`lessons_learned`), prefixed with its prediction accuracy.
    - **Derived (prediction-style)**: synthesized from a matching decision that
      has no usable outcome yet — what was decided and why, marked "not yet
      validated". Repeated runs of the same initiative collapse to one entry.

    Scores lexical overlap between initiative texts; `limit` caps the number of
    source decisions (validated first, derived filling the remainder). Returns []
    when nothing relevant is found.
    `decisions` must be in chronological order (oldest first) for the dedup
    "keep most recent" guarantee to hold.
    """
    by_id = {
        outcome.decision_id: outcome
        for outcome in outcomes
        if not outcome.failed and outcome.lessons_learned
    }
    query = _tokens(f"{initiative.title} {initiative.description}")
    if not query:
        return []

    # Split matching decisions into outcome-backed ("validated") and
    # prediction-only ("derived"). A decision is derived when it produced no
    # usable lesson via an outcome but still carries a real recommendation.
    validated: list[tuple[int, DecisionRecord, OutcomeRecord]] = []
    derived: list[tuple[int, DecisionRecord]] = []
    for decision in decisions:
        past = _tokens(f"{decision.initiative.title} {decision.initiative.description}")
        overlap = len(query & past)
        if overlap == 0 and decision.decision_id not in also_relevant:
            continue
        if overlap == 0:
            # Semantic-only match: floor the score so it ranks below any lexical
            # overlap but still participates in selection/dedup.
            overlap = 1
        outcome = by_id.get(decision.decision_id)
        if outcome is not None:
            validated.append((overlap, decision, outcome))
        elif not decision.recommendation.failed:
            derived.append((overlap, decision))

    validated.sort(key=lambda item: item[0], reverse=True)

    # Collapse repeated runs of the same initiative to one derived entry,
    # keeping the most recent (decisions arrive in chronological order, so the
    # last occurrence wins). Then rank by overlap.
    deduped: dict[str, tuple[int, DecisionRecord]] = {}
    for overlap, decision in derived:
        deduped[decision.initiative.title.lower()] = (overlap, decision)
    derived_ranked = sorted(deduped.values(), key=lambda item: item[0], reverse=True)

    lessons: list[str] = []
    # Validated (outcome-backed) lessons rank first — observed, not predicted.
    selected_validated = validated[:limit]
    for _, decision, outcome in selected_validated:
        for lesson in outcome.lessons_learned:
            lessons.append(
                f'From "{decision.initiative.title}" '
                f"(prediction accuracy {outcome.prediction_accuracy:.0%}): {lesson}"
            )
    # Fill the remaining decision budget with prediction-style derived lessons.
    remaining = limit - len(selected_validated)
    for _, decision in derived_ranked[:remaining]:
        lessons.append(_derived_lesson(decision))
    return lessons
