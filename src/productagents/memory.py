"""Append-only logs (decisions and outcomes) — the organizational-memory stub."""

from pathlib import Path

from productagents.schemas import DecisionRecord, OutcomeRecord

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
