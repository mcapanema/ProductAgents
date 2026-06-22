from textual.app import App

from productagents.tui.degraded import DegradedRunScreen


class _Host(App):
    def __init__(self, results):
        super().__init__()
        self._results = results

    def on_mount(self):
        self.push_screen(DegradedRunScreen(), self._results.append)


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
