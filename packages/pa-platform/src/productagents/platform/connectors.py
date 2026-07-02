"""Composition root for connector sync: load DB-backed config, validate it
(typed, fail-fast), build connectors, run the sync, and persist cursors.

This is the only module that imports the connector framework AND the storage
layer at once — it is the wiring `pa-app` is permitted (arch §2). Connector
config lives in the workspace DB (``connector_config`` table); a legacy
``connectors.yaml`` is imported once (see ``load_db_config``) and then renamed
out of the way. Secrets are *referenced* (a ``*_env`` key names an env var),
never inlined.
"""

import asyncio
import os
from collections.abc import Mapping
from dataclasses import dataclass, field

import yaml
from pydantic import ValidationError

from productagents.connectors import (
    CanonicalSink,
    Connector,
    ConnectorConfig,
    HealthStatus,
    SyncCursor,
    SyncResult,
    discover,
    run_sync,
    span,
)
from productagents.knowledge import DbCanonicalSink, SyncStateStore
from productagents.knowledge.repositories.sqlmodel.engine import (
    create_all,
    make_sessionmaker,
)
from productagents.memory.store import create_all as memory_create_all
from productagents.memory.workspace_state import ConnectorConfigStore

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


async def load_db_config(
    sessionmaker, *, config_path: str | None = None
) -> dict[str, dict]:
    """Raw connector blocks from the DB, importing a legacy YAML file once.

    First read on a fresh DB: if ``connector_config`` is empty and the YAML
    exists, import its blocks verbatim and rename the file to
    ``<path>.imported`` (inert backup). A non-empty table ignores the YAML
    entirely. Secret *references* (``*_env`` keys) are imported as-is; secret
    values never enter the database.
    """
    async with sessionmaker() as session:
        store = ConnectorConfigStore(session)
        blocks = await store.all()
        if blocks:
            return blocks
        path = config_path or connectors_file()
        raw = load_raw_config(path)
        if not raw:
            return {}
        for key, block in raw.items():
            await store.set(key, dict(block or {}))
        os.replace(path, path + ".imported")
        return await store.all()


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
    if not isinstance(raw, Mapping):
        return ConnectorPlan(
            problems=["connectors config: 'connectors' must be a mapping"]
        )
    configs: dict[str, ConnectorConfig] = {}
    problems: list[str] = []
    for key, block in raw.items():
        if block and not isinstance(block, Mapping):
            problems.append(f"connector '{key}': config must be a mapping")
            continue
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
        resolved.pop("enabled", None)  # ponytail: drop meta-key before Pydantic sees it
        try:
            configs[key] = connector_cls.config_cls.model_validate(resolved)
        except ValidationError as exc:
            msg = f"connector '{key}': invalid config — {exc.errors()[0]['msg']}"
            problems.append(msg)
    return ConnectorPlan(configs=configs, problems=problems)


def build_connectors(
    configs: dict[str, ConnectorConfig],
    registry: dict[str, type[Connector]],
    sink: CanonicalSink,
) -> list[Connector]:
    """Instantiate each validated connector against the shared sink."""
    return [registry[key](config, sink) for key, config in configs.items()]


@dataclass(frozen=True)
class SyncReport:
    """The result of one sync pass: per-connector results + config problems."""

    results: list[SyncResult] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


async def run_connector_sync(
    *,
    config_path: str | None = None,
    registry: dict[str, type[Connector]] | None = None,
    engine=None,
    env: dict | None = None,
) -> SyncReport:
    """Load config, sync every enabled connector, persist returned cursors.

    Reads canonical/sync-state schema into existence first (idempotent local
    bootstrap; Alembic remains the migration source of truth). Connectors write
    to the shared canonical store via ``DbCanonicalSink``; cursors round-trip
    through ``SyncStateStore`` as strings.
    """
    # Imported lazily so importing this module for the static planner does not
    # pull in the (heavier) decision_context graph wiring.
    from productagents.platform.context import get_engine

    env = env if env is not None else dict(os.environ)
    registry = registry if registry is not None else discover()
    engine = engine if engine is not None else get_engine()
    sessionmaker = make_sessionmaker(engine)
    await create_all(engine)  # bootstrap canonical_record + sync_state locally
    await memory_create_all(engine)

    raw = await load_db_config(sessionmaker, config_path=config_path)
    plan = plan_connectors(raw, registry, env)
    if not plan.configs:
        return SyncReport(results=[], problems=plan.problems)

    sink = DbCanonicalSink(sessionmaker)
    connectors = build_connectors(plan.configs, registry, sink)

    async with sessionmaker() as session:
        stored = await SyncStateStore(session).cursors()
    cursor_map: dict[str, SyncCursor | None] = {
        key: SyncCursor(value=value)
        for key, value in stored.items()
        if value is not None
    }

    results = await run_sync(connectors, cursor_map)

    async with sessionmaker() as session:
        store = SyncStateStore(session)
        for result in results:
            if result.ok and result.cursor is not None:
                await store.save(result.connector, result.cursor.value)
    return SyncReport(results=results, problems=plan.problems)


async def last_sync_times(*, engine=None) -> dict[str, str]:
    """Each connector's last sync timestamp from the sync_state table (no sync run).

    ponytail: only connectors that have ever persisted a cursor appear here — a
    sync that wrote 0 rows with no cursor change leaves no timestamp. Good enough
    for a 'last synced' badge; add an explicit sync-attempt log if that matters.
    """
    from productagents.platform.context import get_engine

    engine = engine if engine is not None else get_engine()
    await create_all(engine)  # idempotent local bootstrap of sync_state
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        return await SyncStateStore(session).last_synced()


async def connector_plan(
    *,
    registry: Mapping[str, type[Connector]] | None = None,
    env: Mapping | None = None,
    engine=None,
) -> ConnectorPlan:
    """The fail-fast preflight: load blocks from the DB + validate, no sync."""
    from productagents.platform.context import get_engine

    env = env if env is not None else dict(os.environ)
    registry = registry if registry is not None else discover()
    engine = engine if engine is not None else get_engine()
    await memory_create_all(engine)  # idempotent local bootstrap
    maker = make_sessionmaker(engine)
    raw = await load_db_config(maker)
    return plan_connectors(raw, registry, env)


def describe_plan(plan: ConnectorPlan) -> str:
    """A one-line connector-config readiness summary for the home screen."""
    parts: list[str] = []
    if plan.configs:
        names = ", ".join(sorted(plan.configs))
        parts.append(f"{len(plan.configs)} connector(s) enabled: {names}")
    else:
        parts.append("No connectors configured")
    if plan.problems:
        parts.append("⚠ " + "; ".join(plan.problems))
    return " · ".join(parts)


def describe_report(report: SyncReport) -> str:
    """A one-line summary of a completed sync pass."""
    parts: list[str] = []
    for result in report.results:
        if result.ok:
            parts.append(f"{result.connector}: ✓ {result.written} written")
        else:
            parts.append(f"{result.connector}: ✗ {result.error}")
    if report.problems:
        parts.append("⚠ " + "; ".join(report.problems))
    return " · ".join(parts) if parts else "No connectors configured"


class _NullSink:
    """A no-op ``CanonicalSink`` for health probes — nothing is written."""

    async def write(self, model) -> None:
        return None

    async def write_many(self, models) -> None:
        return None


@dataclass(frozen=True)
class HealthReport:
    """Per-connector readiness, plus any static config problems."""

    statuses: dict[str, HealthStatus] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


async def check_connector_health(
    *,
    config_path: str | None = None,
    registry: dict[str, type[Connector]] | None = None,
    env: dict | None = None,
    engine=None,
) -> HealthReport:
    """Probe every enabled connector's readiness (auth + reachability).

    Config now lives in the DB, so this needs storage to read it — a no-op
    sink is still used so health probes never write canonical data. Each
    probe runs in a ``connector.health`` span and concurrently with its
    siblings.
    """
    from productagents.platform.context import get_engine

    env = env if env is not None else dict(os.environ)
    registry = registry if registry is not None else discover()
    engine = engine if engine is not None else get_engine()
    await memory_create_all(engine)
    raw = await load_db_config(make_sessionmaker(engine), config_path=config_path)
    plan = plan_connectors(raw, registry, env)
    if not plan.configs:
        return HealthReport(problems=plan.problems)

    connectors = build_connectors(plan.configs, registry, _NullSink())

    async def _probe(connector: Connector) -> tuple[str, HealthStatus]:
        with span("connector.health", connector=connector.key) as attrs:
            status = await connector.health_check()
            attrs["status"] = "ok" if status.ok else "error"
        return connector.key, status

    pairs = await asyncio.gather(*(_probe(c) for c in connectors))
    return HealthReport(statuses=dict(pairs), problems=plan.problems)


def describe_health(report: HealthReport) -> str:
    """A one-line connector-health summary for the home screen."""
    parts: list[str] = []
    for key, status in report.statuses.items():
        if status.ok:
            parts.append(f"{key}: ✓ healthy")
        else:
            parts.append(f"{key}: ✗ {status.detail}")
    if report.problems:
        parts.append("⚠ " + "; ".join(report.problems))
    return " · ".join(parts) if parts else "No connectors configured"
