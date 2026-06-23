from productagents.core.schemas import (
    AnalystReport,
    DebateTurn,
    Initiative,
    Recommendation,
)

from productagents.agents._format import (
    format_initiative,
    format_recommendation,
    format_reports_brief,
    format_transcript,
)


def _report():
    return AnalystReport(
        analyst="customer_research",
        role="Customer Research Analyst",
        findings=["demand"],
        signals=["tickets"],
    )


def test_format_initiative_renders_two_lines():
    out = format_initiative(Initiative(title="Add SSO", description="Enterprise SSO"))
    assert out == "Initiative: Add SSO\nDescription: Enterprise SSO"


def test_format_reports_brief_one_line_per_report():
    out = format_reports_brief([_report()])
    assert out == "- Customer Research Analyst: findings=['demand'] signals=['tickets']"


def test_format_reports_brief_empty():
    assert format_reports_brief([]) == "(no analyst reports)"


def test_format_transcript_one_line_per_turn():
    turns = [DebateTurn(round=1, side="advocate", argument="build it")]
    assert format_transcript(turns) == "[round 1] advocate: build it"


def test_format_transcript_custom_empty_label():
    assert format_transcript([], empty="(no prior arguments yet)") == (
        "(no prior arguments yet)"
    )


def test_format_transcript_default_empty_label():
    assert format_transcript([]) == "(no debate)"


def test_format_recommendation_renders_canonical_block():
    rec = Recommendation(
        recommendation="Build SSO",
        confidence=0.8,
        rationale="Strong demand",
        expected_outcomes=["unblock deals"],
    )
    assert format_recommendation(rec) == (
        "Recommendation: Build SSO\n"
        "Confidence: 80%\n"
        "Rationale: Strong demand\n"
        "Expected outcomes: ['unblock deals']"
    )


def test_format_recommendation_handles_none():
    assert format_recommendation(None) == "(no recommendation)"
