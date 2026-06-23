from productagents.core.schemas import Evidence
from textual.app import App
from textual.widgets import Static

from productagents.tui.app import ProductAgentsApp
from productagents.tui.degraded import DegradedRunScreen


class _Host(App):
    def __init__(self, results):
        super().__init__()
        self._results = results

    def on_mount(self):
        self.push_screen(DegradedRunScreen(), self._results.append)


def _build_app(*, runner):
    evidence = Evidence(
        scenario="sample", customer_feedback="x", product_analytics={"a": 1}
    )
    return ProductAgentsApp(
        runner,
        evidence,
        recorder=lambda r: None,
        reader=lambda: [],
        outcome_reader=lambda: [],
        show_home=False,
    )


async def test_run_aborted_shows_error_banner():
    from productagents.agents.runner import RunAbortedEvent

    async def _fake_runner(
        initiative, evidence, *, portfolio=None, outcomes=None, approver=None
    ):
        yield RunAbortedEvent(
            node="customer_research",
            category="rate_limit",
            message="Rate limit reached for the configured model. Wait and retry…",
        )

    app = _build_app(runner=_fake_runner)
    async with app.run_test() as pilot:
        pilot.app.query_one("#initiative-title").value = "Add SSO"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        status = str(app.query_one("#status-log", Static).content)
        assert "Rate limit reached" in status


async def test_retry_button_returns_retry():
    results = []
    app = _Host(results)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#retry")
        await pilot.pause()

    assert results == ["retry"]


async def test_decide_button_returns_decide():
    results = []
    app = _Host(results)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#decide")
        await pilot.pause()

    assert results == ["decide"]


async def test_quit_button_returns_quit():
    results = []
    app = _Host(results)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#quit")
        await pilot.pause()

    assert results == ["quit"]
