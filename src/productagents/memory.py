"""Append-only logs (decisions and outcomes) — the organizational-memory stub."""

import re
from pathlib import Path

from productagents.schemas import DecisionRecord, Initiative, OutcomeRecord

DEFAULT_LOG_PATH = Path("decisions.jsonl")
DEFAULT_OUTCOME_LOG_PATH = Path("outcomes.jsonl")


def _path(path: Path | None) -> Path:
    return path if path is not None else DEFAULT_LOG_PATH


def record_decision(record: DecisionRecord, path: Path | None = None) -> None:
    """Append one decision record as a JSON line."""
    target = _path(path)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")


def read_decisions(path: Path | None = None) -> list[DecisionRecord]:
    """Read all decision records; return [] if the log does not exist."""
    target = _path(path)
    if not target.is_file():
        return []
    records = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(DecisionRecord.model_validate_json(line))
    return records


def _outcome_path(path: Path | None) -> Path:
    return path if path is not None else DEFAULT_OUTCOME_LOG_PATH


def record_outcome(outcome: OutcomeRecord, path: Path | None = None) -> None:
    """Append one outcome record as a JSON line."""
    target = _outcome_path(path)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(outcome.model_dump_json() + "\n")


def read_outcomes(path: Path | None = None) -> list[OutcomeRecord]:
    """Read all outcome records; return [] if the log does not exist."""
    target = _outcome_path(path)
    if not target.is_file():
        return []
    outcomes = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            outcomes.append(OutcomeRecord.model_validate_json(line))
    return outcomes


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


def select_relevant_lessons(
    initiative: Initiative,
    decisions: list[DecisionRecord],
    outcomes: list[OutcomeRecord],
    *,
    limit: int = 3,
) -> list[str]:
    """Return formatted lessons from the past decisions most similar to `initiative`.

    Pairs each prior decision with its recorded outcome (by `decision_id`), scores
    lexical overlap between the initiative texts, and returns all lessons from the
    top `limit` matching decisions (each decision may contribute multiple lessons).
    Decisions whose outcome is missing, failed, or has no captured lessons are ignored.
    Returns [] when nothing relevant is found.
    """
    by_id = {
        outcome.decision_id: outcome
        for outcome in outcomes
        if not outcome.failed and outcome.lessons_learned
    }
    query = _tokens(f"{initiative.title} {initiative.description}")
    if not query:
        return []

    scored: list[tuple[int, DecisionRecord, OutcomeRecord]] = []
    for decision in decisions:
        outcome = by_id.get(decision.decision_id)
        if outcome is None:
            continue
        past = _tokens(f"{decision.initiative.title} {decision.initiative.description}")
        overlap = len(query & past)
        if overlap == 0:
            continue
        scored.append((overlap, decision, outcome))

    scored.sort(key=lambda item: item[0], reverse=True)

    lessons: list[str] = []
    for _, decision, outcome in scored[:limit]:
        for lesson in outcome.lessons_learned:
            lessons.append(
                f'From "{decision.initiative.title}" '
                f"(prediction accuracy {outcome.prediction_accuracy:.0%}): {lesson}"
            )
    return lessons
