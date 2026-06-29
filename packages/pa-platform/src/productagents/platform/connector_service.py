"""ConnectorService — the platform face of connector sync + health."""

from productagents.platform import connectors
from productagents.platform.connectors import ConnectorPlan, HealthReport, SyncReport


class ConnectorService:
    def plan(self) -> ConnectorPlan:
        """The static, no-I/O view: which connectors are configured + problems."""
        return connectors.static_connector_plan()

    async def sync(self) -> SyncReport:
        return await connectors.run_connector_sync()

    async def health(self) -> HealthReport:
        return await connectors.check_connector_health()
