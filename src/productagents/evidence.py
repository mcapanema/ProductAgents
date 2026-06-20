"""Load mock evidence for a named scenario from bundled data files."""

import json
from pathlib import Path

from productagents.schemas import Evidence

SCENARIOS_DIR = Path(__file__).parent / "data" / "scenarios"

_FEEDBACK_FILE = "customer_feedback.md"
_ANALYTICS_FILE = "product_analytics.json"
_MARKET_FILE = "market_intelligence.md"
_BUSINESS_FILE = "business_metrics.json"
_TECHNICAL_FILE = "technical_context.md"


class EvidenceError(Exception):
    """Raised when a scenario is missing or its files are malformed."""


def _base(base_dir: Path | None) -> Path:
    return base_dir if base_dir is not None else SCENARIOS_DIR


def list_scenarios(base_dir: Path | None = None) -> list[str]:
    root = _base(base_dir)
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def _parse_json_object(text: str, filename: str, name: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EvidenceError(
            f"Malformed {filename} in scenario {name!r}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise EvidenceError(f"{filename} in scenario {name!r} must be a JSON object")
    return data


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
    product_analytics = _parse_json_object(
        analytics_path.read_text(encoding="utf-8"), _ANALYTICS_FILE, name
    )

    market_intelligence = ""
    market_path = scenario_dir / _MARKET_FILE
    if market_path.is_file():
        market_intelligence = market_path.read_text(encoding="utf-8")

    technical_context = ""
    technical_path = scenario_dir / _TECHNICAL_FILE
    if technical_path.is_file():
        technical_context = technical_path.read_text(encoding="utf-8")

    business_metrics: dict = {}
    business_path = scenario_dir / _BUSINESS_FILE
    if business_path.is_file():
        business_metrics = _parse_json_object(
            business_path.read_text(encoding="utf-8"), _BUSINESS_FILE, name
        )

    return Evidence(
        scenario=name,
        customer_feedback=customer_feedback,
        product_analytics=product_analytics,
        market_intelligence=market_intelligence,
        business_metrics=business_metrics,
        technical_context=technical_context,
    )
