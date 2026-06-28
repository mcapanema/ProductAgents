"""ConnectorService — the platform face of connector sync + health."""

from productagents.platform import connectors
from productagents.platform.connectors import HealthReport, SyncReport


class ConnectorService:
    async def sync(self) -> SyncReport:
        return await connectors.run_connector_sync()

    async def health(self) -> HealthReport:
        return await connectors.check_connector_health()
