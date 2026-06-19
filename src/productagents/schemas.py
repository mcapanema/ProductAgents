"""Strongly-typed schemas shared across agents, graph state, and persistence."""

from pydantic import BaseModel, Field


class Initiative(BaseModel):
    """A product proposal under evaluation."""

    title: str
    description: str


class Evidence(BaseModel):
    """Mock evidence loaded from a named scenario."""

    scenario: str
    customer_feedback: str
    product_analytics: dict


class AnalystFindings(BaseModel):
    """Structured output an analyst LLM call must produce."""

    findings: list[str] = Field(
        description="Key conclusions drawn from the evidence."
    )
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


class Recommendation(BaseModel):
    """The strategist's decision proposal."""

    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    expected_outcomes: list[str]


class DecisionRecord(BaseModel):
    """A persisted record of one decision run."""

    initiative: Initiative
    recommendation: Recommendation
    reports: list[AnalystReport]
    timestamp: str
