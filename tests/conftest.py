"""Shared fixtures for the test suite.

decision_inputs: a standard (Initiative, evidence_spec, context_opener) triple
backed by FakeChatModel so any graph run works offline — HITL and non-HITL
alike. context_opener is a zero-arg callable returning an async CM that
yields an AgentContext — matching DecisionService's constructor. The HITL
distinction lives in DecisionService(human_in_the_loop=True), not in the model.
"""

from contextlib import asynccontextmanager

import pytest

from productagents.agents.context import AgentContext
from productagents.core.models import (
    AnalystFindings,
    DebateArgument,
    DecisionRecord,
    GovernanceFinding,
    Initiative,
    JudgeFinding,
    Recommendation,
    RiskFinding,
)
from tests.fakes import FakeChatModel


@pytest.fixture
def make_decision_record():
    """Factory for a minimal valid DecisionRecord, keyed by decision_id."""

    def _make(decision_id="d1", title="Add enterprise SSO") -> DecisionRecord:
        return DecisionRecord(
            decision_id=decision_id,
            initiative=Initiative(title=title, description="desc"),
            recommendation=Recommendation(
                recommendation="Build it",
                confidence=0.7,
                rationale="r",
                expected_outcomes=["o"],
            ),
            reports=[],
            timestamp="2026-06-19T12:00:00+00:00",
        )

    return _make


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


def _opener_for(ctx: AgentContext):
    """Wrap a pre-built AgentContext as a zero-arg async context manager."""

    @asynccontextmanager
    async def _open():
        yield ctx

    return _open


@pytest.fixture
def decision_inputs():
    """Standard (initiative, evidence_spec, context_opener) for a graph run.

    Also used for HITL runs — the governance verdict is non-error so the
    graph interrupts for human approval when human_in_the_loop=True.
    """
    initiative = Initiative(title="Add SSO", description="Enterprise SSO")
    context = AgentContext(model=_standard_fake_model())
    return initiative, "sample", _opener_for(context)
