from productagents.schemas import Recommendation
from productagents.tui._format import (
    confidence_meter,
    format_debate_turn,
    format_governance,
    format_judgment,
    format_recall_body,
    format_recommendation,
    format_risk_line,
)


def test_confidence_meter_renders_filled_blocks_and_percent():
    bar = confidence_meter(0.81, width=9)
    assert bar.endswith("81%")
    assert bar.count("█") == 7
    assert bar.count("░") == 2


def test_confidence_meter_clamps_and_rounds():
    assert confidence_meter(0.0).endswith("0%")
    assert confidence_meter(1.0).endswith("100%")
    assert confidence_meter(0.82).endswith("82%")


def test_format_recall_body_lists_lessons():
    body = format_recall_body(["lesson one", "lesson two"])
    assert "• lesson one" in body
    assert "• lesson two" in body


def test_format_recall_body_empty_state_points_to_reflection():
    body = format_recall_body([])
    assert "ctrl+r" in body
    assert "no relevant past decisions found" in body.lower()


def test_format_recommendation_has_headline_meter_and_outcomes():
    rec = Recommendation(
        recommendation="Build SSO now",
        confidence=0.82,
        rationale="strong demand",
        expected_outcomes=["enterprise unblock"],
    )
    text = format_recommendation(rec)
    assert "Build SSO now" in text
    assert "82%" in text
    assert "strong demand" in text
    assert "• enterprise unblock" in text


def test_format_judgment_shows_pass_with_both_meters():
    text = format_judgment(True, 1, 0.9, 0.9, "ok")
    assert "PASS" in text
    assert text.count("█") > 0  # at least one meter rendered
    assert "ok" in text


def test_format_judgment_shows_fail():
    assert "FAIL" in format_judgment(False, 2, 0.4, 0.5, "weak grounding")


def test_format_debate_turn_keeps_lowercase_side_and_round():
    text = format_debate_turn("advocate", 2, "ship it")
    assert "advocate" in text
    assert "round 2" in text
    assert "ship it" in text


def test_format_risk_line_includes_role_level_and_rationale():
    text = format_risk_line("Delivery Risk Reviewer", "medium", "some delivery risk")
    assert "Delivery Risk Reviewer" in text
    assert "medium" in text
    assert "some delivery risk" in text


def test_format_governance_plain_and_final():
    assert "approve" in format_governance("approve", "best use")
    final = format_governance("approve", "ok", decided_by="human")
    assert "approve" in final
    assert "human" in final
