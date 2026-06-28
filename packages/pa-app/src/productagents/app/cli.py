"""Command-line client of the ProductAgents Application Layer.

A thin presentation adapter: it parses arguments and invokes platform
Application Services (WorkflowService, WorkspaceService, SessionService) — the
same services the TUI uses. It never imports agents, memory, or connectors
directly. Given no subcommand it launches the TUI; otherwise it runs the named
command headlessly.
"""

from __future__ import annotations

import argparse
import asyncio

from productagents.app.tui.app import launch_tui
from productagents.core.config import load_env
from productagents.core.logging_config import configure_logging
from productagents.core.models import Initiative
from productagents.platform import events as ev
from productagents.platform.connectors import describe_report, run_connector_sync
from productagents.platform.context import make_recorder
from productagents.platform.llm import get_model
from productagents.platform.workflow import WorkflowService
from productagents.platform.workspace import WorkspaceService


def render_event(event: ev.Event) -> str | None:
    """One display line for a platform event, or None to skip it.

    The CLI's equivalent of the TUI's per-event panel routing — text instead of
    widgets. Unhandled event types render nothing.
    """
    if isinstance(event, ev.SessionStarted):
        return f"▶ session {event.session_id} — {event.workflow}"
    if isinstance(event, ev.NodeProgress):
        return f"  · {event.node}: {event.message}"
    if isinstance(event, ev.AnalystCompleted):
        return f"  ✓ {event.node}"
    if isinstance(event, ev.DebateTurnEmitted):
        return f"  ⚔ R{event.round} {event.side}: {event.argument[:80]}"
    if isinstance(event, ev.LessonsRecalled):
        return f"  ↺ {len(event.lessons)} prior lesson(s)"
    if isinstance(event, ev.Recommended):
        rec = event.recommendation
        return f"  ★ recommendation ({rec.confidence:.0%}): {rec.recommendation}"
    if isinstance(event, ev.Judged):
        verdict = "PASS" if event.passed else "FAIL"
        return f"  ⚖ judge {verdict} (attempt {event.attempt})"
    if isinstance(event, ev.RiskAssessed):
        return f"  ⚠ risk {event.level} [{event.reviewer}]"
    if isinstance(event, ev.GovernanceAdvised):
        return f"  ⚑ governance: {event.verdict}"
    if isinstance(event, ev.FinalVerdict):
        return f"  ⚑ final: {event.verdict} (by {event.decided_by})"
    if isinstance(event, ev.NodeFailed):
        return f"  ! {event.node} degraded: {event.message}"
    if isinstance(event, ev.SessionFailed):
        return f"✖ aborted at {event.node} ({event.category}): {event.message}"
    if isinstance(event, ev.SessionFinished):
        rec = event.recommendation
        if rec is None:
            return "✓ finished (no recommendation)"
        return f"✓ finished — {rec.recommendation} (confidence {rec.confidence:.0%})"
    return None


async def run_workflow(
    workflow_name: str, title: str, evidence_spec: str, *, service
) -> int:
    """Run a workflow and stream its events to stdout. Returns 1 if the run
    aborted (a SessionFailed event), else 0."""
    initiative = Initiative(title=title, description=title)
    _session, stream = service.run(workflow_name, initiative, evidence_spec)
    failed = False
    async for event in stream:
        if isinstance(event, ev.SessionFailed):
            failed = True
        line = render_event(event)
        if line is not None:
            print(line)
    return 1 if failed else 0


def _build_run_service() -> WorkflowService:
    """Production WorkflowService for headless runs: real model, DB recorder,
    no human-in-the-loop (governance stays advisory and the run completes)."""
    model = get_model()
    return WorkflowService.for_model(
        model, recorder=make_recorder(), human_in_the_loop=False
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="productagents",
        description="Local operating environment for product decisions.",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="workspace name (default: PRODUCTAGENTS_WORKSPACE or 'default')",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("sync", help="run one connector sync and exit")

    p_run = sub.add_parser("run", help="run a workflow and stream its events")
    p_run.add_argument("workflow", help="workflow name, e.g. evaluate_initiative")
    p_run.add_argument("title", help="initiative title / description")
    p_run.add_argument("--evidence", default="", help="scenario name or directory path")

    return parser


def sync_command(*, syncer=run_connector_sync) -> int:
    """Run one connector sync headlessly, print the report, return an exit code.

    For cron/launchd: ``productagents sync``. Returns 1 if any connector failed
    or the config had problems so the scheduler/CI surfaces it; 0 otherwise.
    ponytail: print (not the file logger) because no TUI owns the terminal here.
    """
    report = asyncio.run(syncer())
    print(describe_report(report))
    failed = any(not r.ok for r in report.results) or bool(report.problems)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    workspaces = WorkspaceService()
    workspace = workspaces.resolve(args.workspace)
    workspaces.activate(workspace)
    load_env()
    configure_logging()

    if args.command is None:
        launch_tui(workspace.name)
        return
    if args.command == "sync":
        raise SystemExit(sync_command())
    if args.command == "run":
        try:
            service = _build_run_service()
        except Exception as exc:
            raise SystemExit(f"cannot start run: {exc}") from exc
        code = asyncio.run(
            run_workflow(args.workflow, args.title, args.evidence, service=service)
        )
        raise SystemExit(code)
    raise SystemExit(f"unknown command: {args.command}")  # pragma: no cover
