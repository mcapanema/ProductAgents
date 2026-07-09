"""Append-only JSONL logs (decisions and outcomes) — the export/audit format.

The DB-backed ``store``/``service`` are the live path from Phase 6 on; these
JSONL helpers remain for export, audit, and offline inspection.
"""

from pathlib import Path

from pydantic import ValidationError

from productagents.core.models import DecisionRecord, OutcomeRecord


def _append_jsonl(record, path: Path) -> None:
    """Append one pydantic record as a JSON line."""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")


def _read_jsonl(path: Path, model_cls):
    """Read+validate every JSON line into ``model_cls``, skipping malformed lines."""
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


def record_decision(record: DecisionRecord, path: Path) -> None:
    """Append one decision record as a JSON line."""
    _append_jsonl(record, path)


def read_decisions(path: Path) -> list[DecisionRecord]:
    """Read all decision records; return [] if the log does not exist."""
    return _read_jsonl(path, DecisionRecord)


def record_outcome(outcome: OutcomeRecord, path: Path) -> None:
    """Append one outcome record as a JSON line."""
    _append_jsonl(outcome, path)


def read_outcomes(path: Path) -> list[OutcomeRecord]:
    """Read all outcome records; return [] if the log does not exist."""
    return _read_jsonl(path, OutcomeRecord)
