"""Shared formatters that render graph state into prompt text.

Several nodes feed the same structures — the analyst reports and the debate
transcript — into their LLM prompts. These helpers keep that rendering in one
place. `format_reports_brief` is the one-line-per-analyst form used where the
reports are context rather than the subject; the strategist keeps its own
detailed, failure-annotated rendering locally because it is the only consumer.
"""

from productagents.schemas import AnalystReport, DebateTurn


def format_reports_brief(reports: list[AnalystReport]) -> str:
    """One line per analyst (role, findings, signals); used by debate and risk."""
    return (
        "\n".join(
            f"- {r.role}: findings={r.findings} signals={r.signals}" for r in reports
        )
        or "(no analyst reports)"
    )


def format_transcript(turns: list[DebateTurn], *, empty: str = "(no debate)") -> str:
    """Render the debate transcript, one line per turn, or `empty` when none."""
    if not turns:
        return empty
    return "\n".join(f"[round {t.round}] {t.side}: {t.argument}" for t in turns)
