"""Strongly-typed schemas shared across agents, graph state, and persistence."""

from uuid import uuid4

from pydantic import BaseModel, Field


class Initiative(BaseModel):
    """A product proposal under evaluation."""

    title: str
    description: str


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
    side: str
    argument: str


class RiskFinding(BaseModel):
    """Structured output a risk reviewer must produce."""

    level: str = Field(
        description="The assessed risk level: one of 'low', 'medium', or 'high'."
    )
    rationale: str = Field(
        description="A short explanation, two to four sentences, justifying the level."
    )


class RiskAssessment(BaseModel):
    """One assembled risk assessment plus identifying metadata set by the node."""

    reviewer: str
    role: str
    level: str
    rationale: str
    failed: bool = False


class Recommendation(BaseModel):
    """The strategist's decision proposal."""

    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    expected_outcomes: list[str]


class GovernanceFinding(BaseModel):
    """Structured output the Product Portfolio Manager must produce."""

    verdict: str = Field(
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

    verdict: str
    rationale: str
    failed: bool = False
    decided_by: str = "ai"
    advisory_verdict: str | None = None
    advisory_rationale: str | None = None


class HumanDecision(BaseModel):
    """A human reviewer's final governance choice, fed back to resume the graph."""

    verdict: str = Field(
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
    initiative: Initiative
    recommendation: Recommendation
    reports: list[AnalystReport]
    debate: list[DebateTurn] = Field(default_factory=list)
    risks: list[RiskAssessment] = Field(default_factory=list)
    governance: GovernanceVerdict | None = None
    prior_lessons: list[str] = Field(default_factory=list)
    evidence_sources: list[EvidenceSourceRef] = Field(default_factory=list)
    timestamp: str
