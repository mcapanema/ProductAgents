"""Shared fixtures for the test suite.

decision_inputs / decision_inputs_hitl: a standard (Initiative, evidence_spec,
AgentContext) triple backed by FakeChatModel so any graph run works offline.
Both fixtures use the same FakeChatModel mapping — the HITL distinction lives in
DecisionService(human_in_the_loop=True), not in the model.
"""

import pytest

from productagents.agents.context import AgentContext
from productagents.core.models import (
    AnalystFindings,
    DebateArgument,
    GovernanceFinding,
    Initiative,
    JudgeFinding,
    Recommendation,
    RiskFinding,
)
from tests.fakes import FakeChatModel


def _standard_fake_model() -> FakeChatModel:
    return FakeChatModel(
        {
            AnalystFindings: AnalystFindings(findings=["f"], signals=["s"]),
            DebateArgument: DebateArgument(argument="an argument"),
            Recommendation: Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            ),
            JudgeFinding: JudgeFinding(
                evidence_grounding_score=0.9,
                rationale_coherence_score=0.9,
                critique="ok",
            ),
            RiskFinding: RiskFinding(level="low", rationale="cheap"),
            GovernanceFinding: GovernanceFinding(
                verdict="approve", rationale="resources well spent"
            ),
        }
    )


@pytest.fixture
def decision_inputs():
    """Standard (initiative, evidence_spec, context) for a non-HITL graph run."""
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    context = AgentContext(model=_standard_fake_model())
    return initiative, "sample", context


@pytest.fixture
def decision_inputs_hitl():
    """Same triple for a HITL run — governance verdict is non-error so the
    graph interrupts for human approval when human_in_the_loop=True."""
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    context = AgentContext(model=_standard_fake_model())
    return initiative, "sample", context
