"""Load mock evidence for a named scenario from bundled data files."""

import json
import logging
from collections.abc import Callable
from importlib.metadata import entry_points
from pathlib import Path
from typing import Protocol

from productagents.core.models import Evidence, EvidenceSourceRef

SCENARIOS_DIR = Path(__file__).parent / "data" / "scenarios"

logger = logging.getLogger(__name__)

_EVIDENCE_GROUP = "productagents.evidence_sources"

# A resolver claims a spec by returning an EvidenceSource, else None.
Resolver = Callable[[str, "Path | None"], "EvidenceSource | None"]

_FEEDBACK_FILE = "customer_feedback.md"
_ANALYTICS_FILE = "product_analytics.json"
_MARKET_FILE = "market_intelligence.md"
_BUSINESS_FILE = "business_metrics.json"
_TECHNICAL_FILE = "technical_context.md"


class EvidenceSource(Protocol):
    """A source that resolves into a fully-populated Evidence object."""

    def collect(self) -> Evidence: ...


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


def _collect_from_dir(
    directory: Path, *, scenario: str, source_label: str, label: str
) -> Evidence:
    feedback_path = directory / _FEEDBACK_FILE
    analytics_path = directory / _ANALYTICS_FILE
    if not feedback_path.is_file():
        raise EvidenceError(f"Missing {_FEEDBACK_FILE} in {label!r}")
    if not analytics_path.is_file():
        raise EvidenceError(f"Missing {_ANALYTICS_FILE} in {label!r}")

    sources: list[EvidenceSourceRef] = []

    customer_feedback = feedback_path.read_text(encoding="utf-8")
    sources.append(
        EvidenceSourceRef(
            field="customer_feedback",
            source=source_label,
            location=str(feedback_path),
        )
    )
    product_analytics = _parse_json_object(
        analytics_path.read_text(encoding="utf-8"), _ANALYTICS_FILE, label
    )
    sources.append(
        EvidenceSourceRef(
            field="product_analytics", source=source_label, location=str(analytics_path)
        )
    )

    market_intelligence = ""
    market_path = directory / _MARKET_FILE
    if market_path.is_file():
        market_intelligence = market_path.read_text(encoding="utf-8")
        sources.append(
            EvidenceSourceRef(
                field="market_intelligence",
                source=source_label,
                location=str(market_path),
            )
        )

    business_metrics: dict = {}
    business_path = directory / _BUSINESS_FILE
    if business_path.is_file():
        business_metrics = _parse_json_object(
            business_path.read_text(encoding="utf-8"), _BUSINESS_FILE, label
        )
        sources.append(
            EvidenceSourceRef(
                field="business_metrics",
                source=source_label,
                location=str(business_path),
            )
        )

    technical_context = ""
    technical_path = directory / _TECHNICAL_FILE
    if technical_path.is_file():
        technical_context = technical_path.read_text(encoding="utf-8")
        sources.append(
            EvidenceSourceRef(
                field="technical_context",
                source=source_label,
                location=str(technical_path),
            )
        )

    return Evidence(
        scenario=scenario,
        customer_feedback=customer_feedback,
        product_analytics=product_analytics,
        market_intelligence=market_intelligence,
        business_metrics=business_metrics,
        technical_context=technical_context,
        sources=sources,
    )


class ScenarioSource:
    """Reads a named scenario from the bundled (or a custom) scenarios directory."""

    def __init__(self, name: str, base_dir: Path | None = None):
        self.name = name
        self.base_dir = base_dir

    def collect(self) -> Evidence:
        directory = _base(self.base_dir) / self.name
        if not directory.is_dir():
            raise EvidenceError(
                f"Scenario not found: {self.name!r} (looked in {directory})"
            )
        return _collect_from_dir(
            directory,
            scenario=self.name,
            source_label=f"scenario:{self.name}",
            label=self.name,
        )


class DirectorySource:
    """Reads evidence files directly from an arbitrary filesystem directory."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def collect(self) -> Evidence:
        if not self.path.is_dir():
            raise EvidenceError(f"Evidence directory not found: {self.path}")
        return _collect_from_dir(
            self.path,
            scenario=self.path.name,
            source_label=f"directory:{self.path}",
            label=str(self.path),
        )


def load_scenario(name: str, base_dir: Path | None = None) -> Evidence:
    return ScenarioSource(name, base_dir).collect()


def _scenario_resolver(spec: str, base_dir: Path | None) -> EvidenceSource | None:
    return ScenarioSource(spec, base_dir) if spec in list_scenarios(base_dir) else None


def _directory_resolver(spec: str, base_dir: Path | None) -> EvidenceSource | None:
    return DirectorySource(Path(spec)) if Path(spec).is_dir() else None


# Built-ins are tried first, preserving the historical order
# (known scenario name → directory path). Third-party resolvers append after.
_BUILTIN_RESOLVERS: list[Resolver] = [_scenario_resolver, _directory_resolver]


def _discovered_resolvers() -> list[Resolver]:
    found: list[Resolver] = []
    for ep in entry_points(group=_EVIDENCE_GROUP):
        try:
            found.append(ep.load())
        except Exception:  # noqa: BLE001 — one bad plugin must not break resolution
            logger.warning(
                "evidence-source plugin %r failed to load; skipping",
                ep.name,
                exc_info=True,
            )
    return found


def collect_evidence(spec: str | None = None, base_dir: Path | None = None) -> Evidence:
    """Resolve a user-supplied source spec to Evidence.

    A falsy spec loads the bundled 'sample' scenario. Otherwise each resolver is
    tried in order — built-ins first (known scenario name → directory path), then
    any third-party resolver registered under ``productagents.evidence_sources``.
    The first resolver that claims the spec wins; if none do, raises EvidenceError.
    """
    if not spec:
        return ScenarioSource("sample", base_dir).collect()
    for resolver in (*_BUILTIN_RESOLVERS, *_discovered_resolvers()):
        source = resolver(spec, base_dir)
        if source is not None:
            return source.collect()
    raise EvidenceError(
        f"No evidence source for {spec!r}: not a known scenario or a directory"
    )
