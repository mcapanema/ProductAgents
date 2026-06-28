"""Pure rendering of connector config readiness and sync outcomes."""

from productagents.connectors.base import ConnectorConfig, SyncResult


def test_describe_plan_no_connectors():
    from productagents.platform.connectors import ConnectorPlan, describe_plan

    assert describe_plan(ConnectorPlan()) == "No connectors configured"


def test_describe_plan_enabled_and_problems():
    from productagents.platform.connectors import ConnectorPlan, describe_plan

    plan = ConnectorPlan(
        configs={"github": ConnectorConfig()},
        problems=["connector 'jira': unknown (not installed)"],
    )
    line = describe_plan(plan)
    assert "1 connector(s) enabled: github" in line
    assert "⚠" in line
    assert "jira" in line


def test_describe_report_lists_results():
    from productagents.platform.connectors import SyncReport, describe_report

    report = SyncReport(
        results=[
            SyncResult(connector="github", written=3, ok=True),
            SyncResult(connector="jira", ok=False, error="boom"),
        ],
        problems=[],
    )
    line = describe_report(report)
    assert "github: ✓ 3 written" in line
    assert "jira: ✗" in line
    assert "boom" in line


def test_describe_report_no_results_with_problems():
    from productagents.platform.connectors import SyncReport, describe_report

    report = SyncReport(results=[], problems=["connector 'x': bad"])
    assert "⚠" in describe_report(report)
    assert "x" in describe_report(report)
