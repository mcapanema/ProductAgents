"""The home menu's Sync action runs the injected syncer and shows the result."""

from textual.widgets import Static

from productagents.app.tui.app import ProductAgentsApp
from productagents.connectors.base import ConnectorConfig, SyncResult
from productagents.platform.connectors import ConnectorPlan, SyncReport


def _ok_status():
    from productagents.app.setup import ConfigStatus

    return ConfigStatus(
        model="anthropic:claude",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=True,
    )


async def test_home_shows_connector_plan_line():
    plan = ConnectorPlan(configs={"github": ConnectorConfig()}, problems=[])
    app = ProductAgentsApp(
        workflow_service=None,
        evidence=None,
        config_checker=_ok_status,
        connector_planner=lambda: plan,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        line = str(app.screen.query_one("#home-connectors", Static).content)
        assert "github" in line


async def test_health_button_runs_checker_and_logs_report():
    from productagents.connectors.base import HealthStatus
    from productagents.platform.connectors import HealthReport

    plan = ConnectorPlan(configs={"github": ConnectorConfig()}, problems=[])
    report = HealthReport(statuses={"github": HealthStatus(ok=True)}, problems=[])

    async def fake_health():
        return report

    app = ProductAgentsApp(
        workflow_service=None,
        evidence=None,
        config_checker=_ok_status,
        connector_planner=lambda: plan,
        connector_health_checker=fake_health,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home-health")
        await pilot.pause()
        line = str(app.screen.query_one("#home-connectors", Static).content)
        assert "github: ✓ healthy" in line


async def test_sync_button_runs_syncer_and_logs_report():
    plan = ConnectorPlan(configs={"github": ConnectorConfig()}, problems=[])
    report = SyncReport(
        results=[SyncResult(connector="github", written=2, ok=True)], problems=[]
    )

    async def fake_syncer():
        return report

    app = ProductAgentsApp(
        workflow_service=None,
        evidence=None,
        config_checker=_ok_status,
        connector_planner=lambda: plan,
        connector_syncer=fake_syncer,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home-sync")
        await pilot.pause()
        line = str(app.screen.query_one("#home-connectors", Static).content)
        assert "github: ✓ 2 written" in line
