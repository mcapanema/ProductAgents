"""The Phase-3 service API is importable from the top-level knowledge package."""

import productagents.knowledge as knowledge


def test_service_surface_is_exported():
    expected = {
        "Page",
        "Query",
        "FeedbackService",
        "FeedbackQuery",
        "InitiativeService",
        "InitiativeQuery",
        "MetricsService",
        "MetricQuery",
        "KnowledgeServices",
        "build_services",
    }
    assert expected <= set(knowledge.__all__)
    for name in expected:
        assert hasattr(knowledge, name), name
