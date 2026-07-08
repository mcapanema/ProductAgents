"""Offline unit test for the per-package coverage-floor logic (no real run)."""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "coverage_floor", Path(__file__).parents[1] / "scripts" / "coverage_floor.py"
)
assert _SPEC is not None
assert _SPEC.loader is not None
cf = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cf)


def _cov() -> dict:
    # Two subpackages: 'app' passes, 'agents' fails a 85% floor.
    return {
        "files": {
            "packages/pa-core/src/productagents/app/cli.py": {
                "summary": {"covered_lines": 90, "num_statements": 100}
            },
            "packages/pa-core/src/productagents/app/ipc.py": {
                "summary": {"covered_lines": 10, "num_statements": 10}
            },
            "packages/pa-core/src/productagents/agents/debate.py": {
                "summary": {"covered_lines": 60, "num_statements": 100}
            },
            "some/unrelated/path.py": {
                "summary": {"covered_lines": 0, "num_statements": 5}
            },
        }
    }


def test_package_totals_buckets_by_subpackage_and_ignores_non_namespace_paths():
    totals = cf.package_totals(_cov())
    assert totals == {"app": (100, 110), "agents": (60, 100)}


def test_below_floor_flags_only_the_weak_package():
    breaches = cf.below_floor(_cov(), 85.0)
    assert breaches == [("agents", 60.0)]


def test_below_floor_empty_when_all_pass():
    assert cf.below_floor(_cov(), 50.0) == []


def test_empty_package_counts_as_full():
    cov = {
        "files": {
            "x/productagents/platform/__init__.py": {
                "summary": {"covered_lines": 0, "num_statements": 0}
            }
        }
    }
    assert cf.below_floor(cov, 90.0) == []
