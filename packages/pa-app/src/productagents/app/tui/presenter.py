"""Routes runner events to panel updates, off the App god-object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Static

from productagents.app.tui._constants import (
    ANALYST_IDS as _ANALYST_IDS,
)
from productagents.app.tui._constants import (
    PANELS as _PANELS,
)
from productagents.app.tui._constants import (
    TITLES as _TITLES,
)
from productagents.app.tui._constants import (
    WIDGET_FOR_NODE as _WIDGET_FOR_NODE,
)
from productagents.app.tui._format import (
    format_debate_turn,
    format_governance,
    format_judgment,
    format_recommendation,
    format_risk_line,
)
from productagents.app.tui._format import format_recall_body as _format_recall_body

if TYPE_CHECKING:
    from productagents.app.tui.app import ProductAgentsApp


class PipelinePresenter:
    """Owns the event→panel rendering that used to live on ProductAgentsApp."""

    def __init__(self, app: ProductAgentsApp) -> None:
        self._app = app
        self._handlers = {
            "NodeProgress": self._on_progress,
            "AnalystCompleted": self._on_node_complete,
            "NodeFailed": self._on_node_error,
            "SessionFailed": self._on_session_failed,
            "DebateTurnEmitted": self._on_debate_turn,
            "RiskAssessed": self._on_risk_assessment,
            "Judged": self._on_judgment,
            "GovernanceAdvised": self._on_governance_verdict,
            "FinalVerdict": self._on_final_verdict,
            "LessonsRecalled": self._on_recall,
            "Recommended": self._on_recommendation,
            "SessionFinished": self._on_finished,
        }

    def dispatch(self, event) -> None:
        # ponytail: string keys — rename an ev.* class → update this dict too
        handler = self._handlers.get(type(event).__name__)
        if handler is not None:
            handler(event)

    def _on_progress(self, event) -> None:
        if event.node in _PANELS:
            self._app.query_one(f"#{event.node}", Static).update(f"… {event.message}")
            if event.node == "strategist":
                self._app._set_state("debate-scroll", "done")
                self._app._rail().set_stage("debate", "done")
                self._app._rail().set_stage("strategy", "running")
            self._app._set_state(event.node, "running")

    def _on_node_complete(self, event) -> None:
        if event.node not in _PANELS:
            return
        report = event.report
        if report.failed:
            self._app.query_one(f"#{event.node}", Static).update(
                "[red]failed — see Status / Errors below[/red]"
            )
            self._app._set_state(event.node, "failed")
        else:
            body = "\n".join(f"• {f}" for f in report.findings) or "(no findings)"
            self._app.query_one(f"#{event.node}", Static).update(body)
            self._app._set_state(event.node, "done")
            if event.node in _ANALYST_IDS:
                rail = self._app._rail()
                rail.bump_analyst()
                if self._app._completed_analysts() >= len(_ANALYST_IDS):
                    rail.set_stage("analysis", "done")

    def _on_node_error(self, event) -> None:
        label = _TITLES.get(_WIDGET_FOR_NODE.get(event.node, event.node), event.node)
        self._app._log_status(f"{label}: {event.message}", level="error")
        self._app._mark_failed(event.node)

    def _on_session_failed(self, event) -> None:
        self._app._log_status(f"run aborted — {event.message}", level="error")
        if event.node:
            self._app._mark_failed(event.node)

    def _on_debate_turn(self, event) -> None:
        self._app._debate_lines.append(
            format_debate_turn(event.side, event.round, event.argument)
        )
        self._app.query_one("#debate", Static).update(
            "\n\n".join(self._app._debate_lines)
        )
        self._app._set_state("debate-scroll", "running")
        self._app._rail().set_stage("analysis", "done")
        self._app._rail().set_stage("debate", "running")

    def _on_risk_assessment(self, event) -> None:
        self._app._risk_lines.append(
            format_risk_line(event.role, event.level, event.rationale)
        )
        self._app.query_one("#risk", Static).update("\n\n".join(self._app._risk_lines))
        self._app._set_state("risk-scroll", "running")
        self._app._rail().set_stage("risk", "running")

    def _on_judgment(self, event) -> None:
        self._app.query_one("#judgment", Static).update(
            format_judgment(
                event.passed,
                event.attempt,
                event.evidence_grounding_score,
                event.rationale_coherence_score,
                event.critique,
            )
        )
        self._app._set_state("strategist", "done")
        self._app._set_state("judgment", "done" if event.passed else "warning")
        self._app._rail().set_stage("strategy", "done")
        self._app._rail().set_stage("judge", "done" if event.passed else "warning")
        self._app._rail().set_stage("risk", "running")

    def _on_governance_verdict(self, event) -> None:
        self._app.query_one("#governance", Static).update(
            format_governance(event.verdict, event.rationale)
        )
        self._app._set_state("risk-scroll", "done")
        state = "done" if event.verdict == "approve" else "warning"
        self._app._set_state("governance", state)
        self._app._rail().set_stage("risk", "done")
        self._app._rail().set_stage(
            "governance", "done" if event.verdict == "approve" else "warning"
        )

    def _on_final_verdict(self, event) -> None:
        self._app.query_one("#governance", Static).update(
            format_governance(
                event.verdict, event.rationale, decided_by=event.decided_by
            )
        )
        state = "done" if event.verdict == "approve" else "warning"
        self._app._set_state("governance", state)
        self._app._rail().set_stage(
            "governance", "done" if event.verdict == "approve" else "warning"
        )

    def _on_recall(self, event) -> None:
        self._app.query_one("#recall", Static).update(
            _format_recall_body(event.lessons)
        )
        self._app._set_state("recall", "done")

    def _on_recommendation(self, event) -> None:
        self._render_strategist_result(event.recommendation)

    def _on_finished(self, event) -> None:
        if event.recommendation is not None:
            self._render_strategist_result(event.recommendation)

    def _render_strategist_result(self, rec) -> None:
        if rec.failed:
            self._app.query_one("#strategist", Static).update(
                "[red]failed — could not synthesize a recommendation. "
                "See Status / Errors below.[/red]"
            )
            self._app._set_state("strategist", "failed")
            return
        self._render_recommendation(rec)
        self._app._set_state("strategist", "done")

    def _render_recommendation(self, recommendation) -> None:
        self._app.query_one("#strategist", Static).update(
            format_recommendation(recommendation)
        )
