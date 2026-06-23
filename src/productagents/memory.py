"""Append-only logs (decisions and outcomes) — the organizational-memory stub."""

import re
from pathlib import Path

from productagents.core.schemas import DecisionRecord, Initiative, OutcomeRecord
from pydantic import ValidationError

DEFAULT_LOG_PATH = Path("decisions.jsonl")
DEFAULT_OUTCOME_LOG_PATH = Path("outcomes.jsonl")


def _path(path: Path | None, default: Path) -> Path:
    return path if path is not None else default


def _append_jsonl(record, path: Path) -> None:
    """Append one pydantic record as a JSON line."""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")


def _read_jsonl(path: Path, model_cls):
    """Read+validate every JSON line into `model_cls`, skipping malformed lines.

    Returns [] if the file does not exist. Blank lines and schema-incompatible
    lines (e.g. legacy records that predate a schema tightening) are skipped
    rather than aborting the read — "degrade, never crash" at the persistence
    boundary.
    """
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(model_cls.model_validate_json(line))
        except ValidationError:
            continue
    return records


def record_decision(record: DecisionRecord, path: Path | None = None) -> None:
    """Append one decision record as a JSON line."""
    _append_jsonl(record, _path(path, DEFAULT_LOG_PATH))


def read_decisions(path: Path | None = None) -> list[DecisionRecord]:
    """Read all decision records; return [] if the log does not exist."""
    return _read_jsonl(_path(path, DEFAULT_LOG_PATH), DecisionRecord)


def record_outcome(outcome: OutcomeRecord, path: Path | None = None) -> None:
    """Append one outcome record as a JSON line."""
    _append_jsonl(outcome, _path(path, DEFAULT_OUTCOME_LOG_PATH))


def read_outcomes(path: Path | None = None) -> list[OutcomeRecord]:
    """Read all outcome records; return [] if the log does not exist."""
    return _read_jsonl(_path(path, DEFAULT_OUTCOME_LOG_PATH), OutcomeRecord)


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


def select_relevant_lessons(
    initiative: Initiative,
    decisions: list[DecisionRecord],
    outcomes: list[OutcomeRecord],
    *,
    limit: int = 3,
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
        if overlap == 0:
            continue
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
