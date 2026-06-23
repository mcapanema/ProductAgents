"""Pure render helpers for the decision console — no Textual, fully testable.

Every function returns a Rich-markup string. Stage colors are the single place
in the .py layer where hex is allowed (they mirror the Theme's stage spectrum).
"""

_ADVOCATE = "#34d399"  # stage-strategy: the "for" voice
_SKEPTIC = "#fb7185"  # stage-risk: the "against" voice


def confidence_meter(value: float, width: int = 9) -> str:
    """A compact block meter, e.g. ``███████░░ 81%``."""
    v = max(0.0, min(1.0, value))
    filled = round(v * width)
    return f"{'█' * filled}{'░' * (width - filled)} {v:.0%}"


def format_recall_body(lessons: list[str]) -> str:
    """Lessons panel body, with a discoverable empty state."""
    if not lessons:
        return (
            "No relevant past decisions found.\n"
            "Run more decisions to build memory, then press ctrl+r to "
            "reflect on their outcomes and feed validated lessons back in."
        )
    return "\n".join(f"• {line}" for line in lessons)


def format_recommendation(rec) -> str:
    """The strategist's proposal as a result card: headline, meter, outcomes."""
    outcomes = "\n".join(f"• {o}" for o in rec.expected_outcomes)
    return (
        f"[b]{rec.recommendation}[/b]\n"
        f"[dim]Confidence[/dim]  {confidence_meter(rec.confidence)}\n\n"
        f"{rec.rationale}\n\n"
        f"[dim]Expected outcomes[/dim]\n{outcomes}"
    )


def format_judgment(
    passed: bool, attempt: int, evidence: float, coherence: float, critique: str
) -> str:
    """Quality-judge verdict with a meter per rubric dimension."""
    badge = "PASS" if passed else "FAIL"
    return (
        f"[b]{badge}[/b] [dim]· attempt {attempt}[/dim]\n\n"
        f"[dim]Evidence [/dim] {confidence_meter(evidence)}\n"
        f"[dim]Coherence[/dim] {confidence_meter(coherence)}\n\n"
        f"{critique}"
    )


def format_debate_turn(side: str, round: int, argument: str) -> str:
    """One debate turn with clear speaker attribution."""
    color = _ADVOCATE if side == "advocate" else _SKEPTIC
    return f"[b {color}]⚔ {side}[/] [dim]· round {round}[/dim]\n  {argument}"


def format_risk_line(role: str, level: str, rationale: str) -> str:
    """One risk reviewer's assessment."""
    return f"[b]{role}[/b] [dim]· {level}[/dim]\n  {rationale}"


def format_governance(
    verdict: str, rationale: str, decided_by: str | None = None
) -> str:
    """The governance verdict; final (human-decided) runs get a clear marker."""
    head = f"FINAL ({decided_by}): {verdict}" if decided_by else verdict
    return f"[b]{head}[/b]\n\n{rationale}"
