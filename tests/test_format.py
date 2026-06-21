from productagents.agents._format import format_reports_brief, format_transcript
from productagents.schemas import AnalystReport, DebateTurn


def _report():
    return AnalystReport(
        analyst="customer_research",
        role="Customer Research Analyst",
        findings=["demand"],
        signals=["tickets"],
    )


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
