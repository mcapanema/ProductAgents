"""The shipped connectors.yaml.example parses and validates against github."""

from pathlib import Path

import productagents.app as app_pkg


def _repo_root() -> Path:
    # packages/pa-app/src/productagents/app -> repo root is parents[5]
    return Path(app_pkg.__file__).resolve().parents[5]


def test_example_file_exists_and_validates():
    from productagents.app.sync import load_raw_config, plan_connectors
    from productagents.connectors.github.connector import GitHubConnector

    example = _repo_root() / "connectors.yaml.example"
    assert example.exists()

    raw = load_raw_config(str(example))
    assert "github" in raw
    # With the referenced env var set, the github block must validate cleanly.
    plan = plan_connectors(raw, {"github": GitHubConnector}, {"GITHUB_TOKEN": "x"})
    assert "github" in plan.configs
    assert plan.problems == []
