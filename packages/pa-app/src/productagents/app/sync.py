"""Composition root for connector sync: load YAML config, validate it (typed,
fail-fast), build connectors, run the sync, and persist cursors.

This is the only module that imports the connector framework AND the storage
layer at once — it is the wiring `pa-app` is permitted (arch §2). The connector
config is read from a YAML file whose secrets are *referenced* (a ``*_env`` key
names an env var), never inlined.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

import yaml
from pydantic import ValidationError

from productagents.connectors import Connector, ConnectorConfig, discover

DEFAULT_CONNECTORS_FILE = "connectors.yaml"


def connectors_file() -> str:
    """Path to the connector config YAML (override with the env var)."""
    return os.environ.get("PRODUCTAGENTS_CONNECTORS_FILE", DEFAULT_CONNECTORS_FILE)


def load_raw_config(path: str) -> dict[str, dict]:
    """Parse the ``connectors:`` block of a YAML file; ``{}`` if it is missing."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data.get("connectors") or {}


@dataclass(frozen=True)
class ConnectorPlan:
    """The result of statically validating the connector config (no I/O)."""

    configs: dict[str, ConnectorConfig] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


def _resolve_secrets(key: str, block: dict, env: Mapping) -> tuple[dict, list[str]]:
    """Turn each ``<field>_env: VAR`` into ``<field>: env[VAR]``; collect misses."""
    resolved = dict(block)
    problems: list[str] = []
    for raw_key in list(resolved):
        if not raw_key.endswith("_env"):
            continue
        field_name = raw_key[: -len("_env")]
        var = resolved.pop(raw_key)
        value = env.get(var)
        if not value:
            msg = (
                f"connector '{key}': env var {var} "
                f"(for field '{field_name}') is not set"
            )
            problems.append(msg)
        else:
            resolved[field_name] = value
    return resolved, problems


def plan_connectors(
    raw: dict[str, dict],
    registry: Mapping[str, type[Connector]],
    env: Mapping,
) -> ConnectorPlan:
    """Validate the config statically: enabled-only, secrets resolved, typed.

    Never touches the network or the database. A connector with any problem is
    omitted from ``configs`` so a misconfigured connector can never run.
    """
    configs: dict[str, ConnectorConfig] = {}
    problems: list[str] = []
    for key, block in raw.items():
        block = block or {}
        if not block.get("enabled", True):
            continue
        connector_cls = registry.get(key)
        if connector_cls is None:
            problems.append(f"connector '{key}': unknown (not installed)")
            continue
        resolved, secret_problems = _resolve_secrets(key, block, env)
        if secret_problems:
            problems.extend(secret_problems)
            continue
        try:
            configs[key] = connector_cls.config_cls.model_validate(resolved)
        except ValidationError as exc:
            msg = f"connector '{key}': invalid config — {exc.errors()[0]['msg']}"
            problems.append(msg)
    return ConnectorPlan(configs=configs, problems=problems)


def static_connector_plan(
    *,
    config_path: str | None = None,
    registry: Mapping[str, type[Connector]] | None = None,
    env: Mapping | None = None,
) -> ConnectorPlan:
    """The fail-fast preflight: load + validate config without running a sync."""
    env = env if env is not None else dict(os.environ)
    registry = registry if registry is not None else discover()
    raw = load_raw_config(config_path or connectors_file())
    return plan_connectors(raw, registry, env)
