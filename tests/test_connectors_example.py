"""The shipped connectors.yaml.example parses and validates against github."""

from pathlib import Path

import productagents.app as app_pkg


def _repo_root() -> Path:
    # packages/pa-app/src/productagents/app -> repo root is parents[5]
    return Path(app_pkg.__file__).resolve().parents[5]


def test_example_file_exists_and_validates():
    from productagents.connectors.github.connector import GitHubConnector
    from productagents.connectors.jira.connector import JiraConnector
    from productagents.connectors.obsidian.connector import ObsidianConnector
    from productagents.platform.connectors import load_raw_config, plan_connectors

    example = _repo_root() / "connectors.yaml.example"
    assert example.exists()

    raw = load_raw_config(str(example))
    assert "github" in raw
    # With all referenced env vars set, every block must validate cleanly.
    registry = {
        "github": GitHubConnector,
        "jira": JiraConnector,
        "obsidian": ObsidianConnector,
    }
    env = {"GITHUB_TOKEN": "x", "JIRA_API_TOKEN": "y"}
    plan = plan_connectors(raw, registry, env)
    assert "github" in plan.configs
    assert "jira" in plan.configs
    assert "obsidian" in plan.configs
    assert plan.problems == []
