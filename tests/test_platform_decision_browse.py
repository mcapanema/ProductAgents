"""Tests for DecisionService.list_decisions / get_decision."""

from productagents.platform.decision_service import DecisionService


async def test_list_decisions_delegates_to_learning(decision_inputs):
    _, _, context = decision_inputs
    service = DecisionService(context)
    decisions = await service.list_decisions()
    assert isinstance(decisions, list)  # empty store → []


async def test_get_decision_returns_none_when_not_found(decision_inputs):
    _, _, context = decision_inputs
    service = DecisionService(context)
    result = await service.get_decision("nonexistent-id")
    assert result is None
