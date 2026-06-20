"""Load mock evidence for a named scenario from bundled data files."""

import json
from pathlib import Path

from productagents.schemas import Evidence

SCENARIOS_DIR = Path(__file__).parent / "data" / "scenarios"

_FEEDBACK_FILE = "customer_feedback.md"
_ANALYTICS_FILE = "product_analytics.json"


class EvidenceError(Exception):
    """Raised when a scenario is missing or its files are malformed."""


def _base(base_dir: Path | None) -> Path:
    return base_dir if base_dir is not None else SCENARIOS_DIR


def list_scenarios(base_dir: Path | None = None) -> list[str]:
    root = _base(base_dir)
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def load_scenario(name: str, base_dir: Path | None = None) -> Evidence:
    scenario_dir = _base(base_dir) / name
    if not scenario_dir.is_dir():
        raise EvidenceError(f"Scenario not found: {name!r} (looked in {scenario_dir})")

    feedback_path = scenario_dir / _FEEDBACK_FILE
    analytics_path = scenario_dir / _ANALYTICS_FILE

    if not feedback_path.is_file():
        raise EvidenceError(f"Missing {_FEEDBACK_FILE} in scenario {name!r}")
    if not analytics_path.is_file():
        raise EvidenceError(f"Missing {_ANALYTICS_FILE} in scenario {name!r}")

    customer_feedback = feedback_path.read_text(encoding="utf-8")
    try:
        product_analytics = json.loads(analytics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(
            f"Malformed {_ANALYTICS_FILE} in scenario {name!r}: {exc}"
        ) from exc

    if not isinstance(product_analytics, dict):
        raise EvidenceError(
            f"{_ANALYTICS_FILE} in scenario {name!r} must be a JSON object"
        )

    return Evidence(
        scenario=name,
        customer_feedback=customer_feedback,
        product_analytics=product_analytics,
    )
