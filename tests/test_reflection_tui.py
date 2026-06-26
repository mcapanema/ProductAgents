from productagents.app.tui.app import ProductAgentsApp
from productagents.core.models import (
    DecisionRecord,
    Initiative,
    OutcomeRecord,
    Recommendation,
)


def _decision():
    return DecisionRecord(
        decision_id="abc123",
        initiative=Initiative(title="Add SSO", description="Enterprise SSO"),
        recommendation=Recommendation(
            recommendation="Build SSO now",
            confidence=0.8,
            rationale="demand",
            expected_outcomes=["enterprise unblock"],
        ),
        reports=[],
        timestamp="2026-06-19T12:00:00+00:00",
    )


async def _decisions_reader(decisions):
    return decisions


def _app(reflector, reader, outcome_recorder):
    return ProductAgentsApp(
        None,
        None,
        reader=reader,
        reflector=reflector,
        outcome_recorder=outcome_recorder,
        show_home=False,
    )


async def test_reflection_mode_records_outcome():
    decision = _decision()
    recorded: list[OutcomeRecord] = []

    async def fake_reflector(d, note):
        return OutcomeRecord(
            decision_id=d.decision_id,
            actual_outcomes=["adoption was slow"],
            prediction_accuracy=0.4,
            lessons_learned=["validate demand earlier"],
            reflected_at="2026-06-20T00:00:00+00:00",
        )

    async def fake_reader():
        return [decision]

    async def fake_outcome_recorder(outcome):
        recorded.append(outcome)

    app = _app(fake_reflector, fake_reader, fake_outcome_recorder)

    async with app.run_test() as pilot:
        await pilot.press("ctrl+r")
        await pilot.pause()
        await pilot.app.workers.wait_for_complete()  # wait for _load_decisions
        # After push_screen, pilot.app.screen is the active ReflectionScreen.
        note = pilot.app.screen.query_one("#outcome-note")
        note.focus()
        note.value = "We shipped but adoption was slow."
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        text = str(pilot.app.screen.query_one("#reflection").content)
        assert "validate demand earlier" in text
        assert "40%" in text

    assert len(recorded) == 1
    assert recorded[0].decision_id == "abc123"
    assert recorded[0].lessons_learned == ["validate demand earlier"]


async def test_reflection_mode_no_decisions_does_nothing():
    recorded: list[OutcomeRecord] = []

    async def fake_reflector(d, note):  # pragma: no cover - must never be called
        raise AssertionError("reflector should not run without a selected decision")

    async def fake_reader():
        return []

    async def fake_outcome_recorder(outcome):
        recorded.append(outcome)

    app = _app(fake_reflector, fake_reader, fake_outcome_recorder)

    async with app.run_test() as pilot:
        await pilot.press("ctrl+r")
        await pilot.pause()
        await pilot.app.workers.wait_for_complete()  # wait for _load_decisions
        # After push_screen, pilot.app.screen is the active ReflectionScreen.
        note = pilot.app.screen.query_one("#outcome-note")
        note.focus()
        note.value = "anything"
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        text = str(pilot.app.screen.query_one("#reflection").content)
        assert "Pick a decision" in text

    assert recorded == []


async def test_reflection_mode_reflector_raises_shows_error():
    decision = _decision()
    recorded: list[OutcomeRecord] = []

    async def boom(d, note):
        raise RuntimeError("LLM down")

    async def fake_reader():
        return [decision]

    async def fake_outcome_recorder(outcome):
        recorded.append(outcome)

    app = _app(boom, fake_reader, fake_outcome_recorder)

    async with app.run_test() as pilot:
        await pilot.press("ctrl+r")
        await pilot.pause()
        await pilot.app.workers.wait_for_complete()  # wait for _load_decisions
        # After push_screen, pilot.app.screen is the active ReflectionScreen.
        note = pilot.app.screen.query_one("#outcome-note")
        note.focus()
        note.value = "We shipped but it flopped."
        await pilot.press("enter")
        await pilot.app.workers.wait_for_complete()
        await pilot.pause()
        text = str(pilot.app.screen.query_one("#reflection").content)
        assert "Reflection failed" in text

    assert recorded == []
