import productagents.core.models as models

# The exact symbol set the v1 codebase imports from core.schemas today. After the
# Task 11 find/replace, every one of these must resolve from core.models.
_V1_PUBLIC = {
    "AnalystFindings",
    "AnalystReport",
    "DebateArgument",
    "DebateTurn",
    "DecisionRecord",
    "Evidence",
    "EvidenceSourceRef",
    "GovernanceFinding",
    "GovernanceVerdict",
    "HumanDecision",
    "Initiative",
    "JudgeFinding",
    "JudgeVerdict",
    "OutcomeRecord",
    "Recommendation",
    "Reflection",
    "RiskAssessment",
    "RiskFinding",
}

_NEW_CANONICAL = {
    "CanonicalModel",
    "CustomerFeedback",
    "SupportTicket",
    "UserSegment",
    "Incident",
    "Feature",
    "RoadmapItem",
    "Objective",
    "KeyResult",
    "ProductMetric",
    "MetricSnapshot",
    "SourceRef",
    "ExternalRef",
}


def test_v1_public_symbols_are_reexported():
    missing = {name for name in _V1_PUBLIC if not hasattr(models, name)}
    assert not missing, f"missing v1 re-exports: {missing}"


def test_new_canonical_symbols_are_exported():
    missing = {name for name in _NEW_CANONICAL if not hasattr(models, name)}
    assert not missing, f"missing canonical exports: {missing}"


def test_initiative_is_the_planning_model():
    from productagents.core.models.planning import Initiative as PlanningInitiative

    assert models.Initiative is PlanningInitiative


def test_all_is_explicit():
    assert set(_V1_PUBLIC | _NEW_CANONICAL).issubset(set(models.__all__))
