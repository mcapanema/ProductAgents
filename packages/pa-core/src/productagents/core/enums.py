"""Shared constrained vocabularies (Literal aliases) for canonical and decision models.

Kept as `Literal` aliases rather than `enum.Enum` so they validate, serialize,
and drive LLM structured output exactly as the v1 schemas did.
"""

from typing import Literal

# --- v1 decision vocabularies (moved verbatim from schemas.py) ---
Verdict = Literal["approve", "reject", "request_analysis"]
RiskLevel = Literal["low", "medium", "high"]
DebateSide = Literal["advocate", "skeptic"]
DecidedBy = Literal["ai", "human"]

# --- canonical-model vocabularies (new in v2) ---
Priority = Literal["low", "medium", "high", "critical"]
Sentiment = Literal["positive", "neutral", "negative"]
InitiativeStatus = Literal["proposed", "planned", "in_progress", "shipped", "cancelled"]
FeatureStatus = Literal["idea", "planned", "in_progress", "shipped", "deprecated"]
TicketStatus = Literal["open", "pending", "resolved", "closed"]
IncidentStatus = Literal["investigating", "identified", "monitoring", "resolved"]
Severity = Literal["sev1", "sev2", "sev3", "sev4"]
