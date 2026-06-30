# packages/pa-core/src/productagents/core/models/decision.py
"""Decision context: the platform-produced records of a decision run.

These are NOT synced canonical entities (no vendor provenance), so they are plain
`BaseModel`s, not `CanonicalModel` subclasses. There are two flavours: the
structured-output schemas an LLM call must return (`AnalystFindings`,
`DebateArgument`, `Recommendation`, …) and the assembled/enriched records nodes
build from them (`AnalystReport`, `DebateTurn`, `DecisionRecord`, …).
"""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from productagents.core.enums import DebateSide, DecidedBy, RiskLevel, Verdict
from productagents.core.models.planning import Initiative


class EvidenceSourceRef(BaseModel):
    """Where one piece of evidence came from, for traceability."""

    field: str = Field(description="The Evidence field this piece populated.")
    source: str = Field(
        description="Source label, e.g. 'scenario:sample' or 'directory:/data/q3'."
    )
    location: str = Field(
        description="Concrete origin, e.g. the file path the data was read from."
    )


class Evidence(BaseModel):
    """Mock evidence loaded from a named scenario."""

    scenario: str
    customer_feedback: str
    product_analytics: dict
    market_intelligence: str = ""
    business_metrics: dict = Field(default_factory=dict)
    technical_context: str = ""
    sources: list[EvidenceSourceRef] = Field(default_factory=list)


class AnalystFindings(BaseModel):
    """Structured output an analyst LLM call must produce."""

    findings: list[str] = Field(description="Key conclusions drawn from the evidence.")
    signals: list[str] = Field(
        description="Specific supporting data points or quotes from the evidence."
    )


class AnalystReport(BaseModel):
    """An analyst's findings plus identifying metadata set by the node."""

    analyst: str
    role: str
    findings: list[str]
    signals: list[str]
    failed: bool = False


class DebateArgument(BaseModel):
    """Structured output a debate agent (advocate or skeptic) must produce."""

    argument: str = Field(
        description="A single focused argument or rebuttal, two to four sentences."
    )


class DebateTurn(BaseModel):
    """One assembled turn in the debate transcript."""

    round: int
    side: DebateSide
    argument: str


class RiskFinding(BaseModel):
    """Structured output a risk reviewer must produce."""

    level: RiskLevel = Field(
        description="The assessed risk level: one of 'low', 'medium', or 'high'."
    )
    rationale: str = Field(
        description="A short explanation, two to four sentences, justifying the level."
    )


class RiskAssessment(BaseModel):
    """One assembled risk assessment plus identifying metadata set by the node."""

    reviewer: str
    role: str
    level: RiskLevel | Literal["unknown"]
    rationale: str
    failed: bool = False


class Recommendation(BaseModel):
    """The strategist's decision proposal."""

    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    expected_outcomes: list[str]
    failed: bool = False


class JudgeFinding(BaseModel):
    """Structured output the quality Judge must produce for a recommendation."""

    evidence_grounding_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "0-1: is every claim in the recommendation supported by the analyst "
            "findings and signals, with no unsupported assertions?"
        ),
    )
    rationale_coherence_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "0-1: does the conclusion follow logically from the stated rationale "
            "and expected outcomes, with no internal contradictions?"
        ),
    )
    critique: str = Field(
        description="Specific, actionable feedback the strategist can use to revise."
    )


class JudgeVerdict(BaseModel):
    """One assembled judge verdict. `passed` is computed by the node from the
    configured threshold, never by the LLM."""

    evidence_grounding_score: float
    rationale_coherence_score: float
    passed: bool
    critique: str
    attempt: int
    failed: bool = False


class GovernanceFinding(BaseModel):
    """Structured output the Product Portfolio Manager must produce."""

    verdict: Verdict = Field(
        description=(
            "The governance verdict: one of 'approve', 'reject', or 'request_analysis'."
        )
    )
    rationale: str = Field(
        description=(
            "A short explanation, two to four sentences, justifying the verdict."
        )
    )


class GovernanceVerdict(BaseModel):
    """One assembled governance verdict plus a failure flag set by the node.

    In human-in-the-loop runs this carries the *final* (human) decision, with the
    AI's advisory recommendation preserved for traceability. In autonomous runs
    `decided_by` stays "ai" and the advisory fields stay None.
    """

    verdict: Verdict | Literal["error"]
    rationale: str
    failed: bool = False
    decided_by: DecidedBy = "ai"
    advisory_verdict: Verdict | None = None
    advisory_rationale: str | None = None


class HumanDecision(BaseModel):
    """A human reviewer's final governance choice, fed back to resume the graph."""

    verdict: Verdict = Field(
        description="One of 'approve', 'reject', or 'request_analysis'."
    )
    rationale: str = ""


class Reflection(BaseModel):
    """Structured output the reflection agent must produce."""

    actual_outcomes: list[str] = Field(
        description="What actually happened as a result of the decision."
    )
    prediction_accuracy: float = Field(
        ge=0.0,
        le=1.0,
        description="How well the predicted expected outcomes matched reality, 0 to 1.",
    )
    lessons_learned: list[str] = Field(
        description="Concrete lessons to apply to future decisions."
    )


class OutcomeRecord(BaseModel):
    """A persisted reflection on a past decision's actual outcome."""

    decision_id: str
    actual_outcomes: list[str]
    prediction_accuracy: float = Field(ge=0.0, le=1.0)
    lessons_learned: list[str]
    reflected_at: str
    failed: bool = False


class DecisionRecord(BaseModel):
    """A persisted record of one decision run."""

    decision_id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str | None = None  # the Session that produced this run, for tracing
    initiative: Initiative
    recommendation: Recommendation
    reports: list[AnalystReport]
    debate: list[DebateTurn] = Field(default_factory=list)
    risks: list[RiskAssessment] = Field(default_factory=list)
    governance: GovernanceVerdict | None = None
    judgment: JudgeVerdict | None = None
    prior_lessons: list[str] = Field(default_factory=list)
    evidence_sources: list[EvidenceSourceRef] = Field(default_factory=list)
    timestamp: str
