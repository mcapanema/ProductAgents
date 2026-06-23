import pytest
from textual.app import App, ComposeResult

from productagents.app.tui.rail import STAGES, PipelineRail, render_rail


def test_stages_are_the_seven_pipeline_stages_in_order():
    keys = [k for k, _ in STAGES]
    assert keys == [
        "evidence",
        "analysis",
        "debate",
        "strategy",
        "judge",
        "risk",
        "governance",
    ]


def test_render_rail_shows_labels_and_analyst_counter():
    states = {k: "queued" for k, _ in STAGES}
    line = render_rail(states, analyst_done=2)
    assert "Evidence" in line
    assert "Governance" in line
    assert "2/5" in line  # analysis counter


def test_render_rail_marks_done_and_running_glyphs():
    states = {k: "queued" for k, _ in STAGES}
    states["evidence"] = "done"
    states["analysis"] = "running"
    line = render_rail(states, analyst_done=3)
    assert "✓" in line  # a done stage
    assert "▸" in line  # a running stage


def test_render_rail_marks_failure_and_warning():
    states = {k: "queued" for k, _ in STAGES}
    states["strategy"] = "failed"
    states["governance"] = "warning"
    line = render_rail(states, analyst_done=5)
    assert "✗" in line
    assert "⚠" in line


class _RailHarness(App):
    def compose(self) -> ComposeResult:
        yield PipelineRail()


@pytest.mark.asyncio
async def test_pipeline_rail_widget_resets_and_advances():
    app = _RailHarness()
    async with app.run_test() as pilot:
        rail = pilot.app.query_one("#pipeline-rail", PipelineRail)
        rail.reset()
        rail.set_stage("evidence", "done")
        rail.bump_analyst()
        rail.bump_analyst()
        rail.set_stage("analysis", "running")
        await pilot.pause()
        text = str(rail.content)
        assert "✓" in text  # evidence done
        assert "2/5" in text  # two analysts counted
        assert "▸" in text  # analysis running
