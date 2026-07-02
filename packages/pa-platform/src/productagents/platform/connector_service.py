"""ConnectorService — the platform face of connector sync + health + config."""

import os

from productagents.connectors import discover
from productagents.knowledge.repositories.sqlmodel.engine import make_sessionmaker
from productagents.memory.store import create_all as memory_create_all
from productagents.memory.workspace_state import ConnectorConfigStore
from productagents.platform import connectors
from productagents.platform.configuration import write_env
from productagents.platform.connectors import (
    ConnectorPlan,
    HealthReport,
    SyncReport,
    load_db_config,
    plan_connectors,
)
from productagents.platform.workspace import WorkspaceService


class ConnectorService:
    def __init__(self, *, engine=None, env_path: str | None = None) -> None:
        self._engine = engine
        self._env_path = env_path

    def _resolved_env_path(self) -> str:
        if self._env_path is not None:
            return self._env_path
        return str(WorkspaceService().resolve(None).env_file)

    async def _blocks(self):
        from productagents.platform.context import get_engine

        engine = self._engine or get_engine()
        await memory_create_all(engine)
        maker = make_sessionmaker(engine)
        return maker, await load_db_config(maker)

    def _entry(self, key, registry, blocks, problems):
        cls = registry.get(key)
        return {
            "connector": key,
            "installed": cls is not None,
            "config": blocks.get(key, {}),
            "schema": cls.config_cls.model_json_schema() if cls else None,
            "problems": [p for p in problems if p.startswith(f"connector '{key}'")],
        }

    async def plan(self) -> ConnectorPlan:
        """The static view: which connectors are configured + problems (no sync)."""
        return await connectors.connector_plan()

    async def sync(self) -> SyncReport:
        return await connectors.run_connector_sync()

    async def health(self) -> HealthReport:
        return await connectors.check_connector_health()

    async def last_synced(self) -> dict[str, str]:
        """Each connector's last successful-sync timestamp (ISO-8601), by key."""
        return await connectors.last_sync_times()

    async def config_list(self, *, registry=None) -> list[dict]:
        """Every installed or configured connector: block + schema + problems."""
        registry = registry if registry is not None else discover()
        _maker, blocks = await self._blocks()
        plan = plan_connectors(blocks, registry, dict(os.environ))
        keys = sorted(set(registry) | set(blocks))
        return [self._entry(k, registry, blocks, plan.problems) for k in keys]

    async def config_save(
        self, connector: str, config: dict, *, secrets=None, registry=None
    ) -> dict:
        """Validate-then-write one connector's block; secrets go to .env only.

        Enabled blocks that fail ``plan_connectors`` are rejected whole (nothing
        half-written). A supplied secret must be referenced by a ``*_env`` field
        of the block being saved — the GUI can never write arbitrary env vars.
        Blank secret values are skipped (never blank a stored secret).
        """
        registry = registry if registry is not None else discover()
        secrets = {k: v for k, v in (secrets or {}).items() if str(v).strip()}
        referenced = {
            v for k, v in config.items() if k.endswith("_env") and isinstance(v, str)
        }
        for var in secrets:
            if var not in referenced:
                raise ValueError(f"secret {var!r} is not referenced by any *_env field")
        env = dict(os.environ) | secrets
        plan = plan_connectors({connector: config}, registry, env)
        if config.get("enabled", True) and plan.problems:
            raise ValueError("; ".join(plan.problems))
        if secrets:
            write_env(secrets, dotenv_path=self._resolved_env_path())
        maker, _ = await self._blocks()
        async with maker() as session:
            await ConnectorConfigStore(session).set(connector, dict(config))
        _maker, blocks = await self._blocks()
        check = plan_connectors(blocks, registry, dict(os.environ))
        return self._entry(connector, registry, blocks, check.problems)
