"""Command-line client of the ProductAgents Application Layer.

A thin presentation adapter: it parses arguments and invokes platform
Application Services (WorkflowService, WorkspaceService, SessionService) — the
same services the GUI uses. It never imports agents, memory, or connectors
directly. Given no subcommand it prints help; otherwise it runs the named
command headlessly.
"""

from __future__ import annotations

import argparse
import asyncio

from productagents.core.config import load_env
from productagents.core.logging_config import configure_logging
from productagents.core.models import Initiative
from productagents.platform import events as ev
from productagents.platform.connectors import describe_report, run_connector_sync
from productagents.platform.context import make_recorder
from productagents.platform.decision_read_service import DecisionReadService
from productagents.platform.llm import get_model
from productagents.platform.prompt_service import PromptService
from productagents.platform.reflection_service import ReflectionService
from productagents.platform.session_service import SessionService
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


async def sessions_list(*, service) -> int:
    """Print one row per persisted session (id, workflow, status, created_at)."""
    sessions = await service.list()
    if not sessions:
        print("no sessions yet")
        return 0
    for s in sessions:
        print(f"{s.id}  {s.workflow}  {s.status}  {s.created_at.isoformat()}")
    return 0


async def sessions_show(session_id: str, *, service) -> int:
    """Replay one session's event timeline. Returns 1 if the id is unknown."""
    session = await service.get(session_id)
    if session is None:
        print(f"no such session: {session_id}")
        return 1
    print(f"▶ session {session.id} — {session.workflow} [{session.status}]")
    for event in await service.events(session_id):
        line = render_event(event)
        if line is not None:
            print(line)
    return 0


def _build_run_service(*, human_in_the_loop: bool = False) -> WorkflowService:
    """Production WorkflowService for runs: real model + DB recorder.

    ``human_in_the_loop`` is False for the headless CLI ``run`` (governance stays
    advisory and the run completes). The IPC adapter builds it ``True`` so a GUI
    run can pause for approval; with no approver the graph still auto-approves.
    """
    model = get_model()
    return WorkflowService.for_model(
        model, recorder=make_recorder(), human_in_the_loop=human_in_the_loop
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
    sub.add_parser("ipc", help="serve the JSON-over-stdio IPC protocol (for the GUI)")
    p_swb = sub.add_parser(
        "serve-ws",
        help="serve the IPC protocol over a localhost WebSocket (dev UI testing)",
    )
    p_swb.add_argument(
        "--port", type=int, default=7420, help="localhost port (default 7420)"
    )

    p_run = sub.add_parser("run", help="run a workflow and stream its events")
    p_run.add_argument("workflow", help="workflow name, e.g. evaluate_initiative")
    p_run.add_argument("title", help="initiative title / description")
    p_run.add_argument("--evidence", default="", help="scenario name or directory path")

    p_ws = sub.add_parser("workspace", help="list or show workspaces")
    ws_sub = p_ws.add_subparsers(dest="ws_command")
    ws_sub.add_parser("list", help="list workspaces")
    p_ws_show = ws_sub.add_parser("show", help="show a workspace's paths")
    p_ws_show.add_argument("name", nargs="?", default=None, help="defaults to active")

    p_se = sub.add_parser("sessions", help="list or replay runtime sessions")
    se_sub = p_se.add_subparsers(dest="se_command")
    se_sub.add_parser("list", help="list persisted sessions")
    p_se_show = se_sub.add_parser("show", help="replay a session's events")
    p_se_show.add_argument("session_id", help="session id to replay")

    p_pr = sub.add_parser("prompts", help="browse, diff, edit, and roll back prompts")
    pr_sub = p_pr.add_subparsers(dest="pr_command")
    pr_sub.add_parser("list", help="list prompt names")
    p_pr_show = pr_sub.add_parser("show", help="print a prompt's text")
    p_pr_show.add_argument("name")
    p_pr_show.add_argument("--version", type=int, default=None)
    p_pr_diff = pr_sub.add_parser("diff", help="unified diff between two versions")
    p_pr_diff.add_argument("name")
    p_pr_diff.add_argument("old", type=int)
    p_pr_diff.add_argument("new", type=int)
    p_pr_save = pr_sub.add_parser("save", help="save FILE as a new version of NAME")
    p_pr_save.add_argument("name")
    p_pr_save.add_argument("file")
    p_pr_rb = pr_sub.add_parser("rollback", help="re-activate an old version")
    p_pr_rb.add_argument("name")
    p_pr_rb.add_argument("version", type=int)

    p_de = sub.add_parser("decisions", help="export recorded decisions")
    de_sub = p_de.add_subparsers(dest="de_command")
    p_de_export = de_sub.add_parser(
        "export", help="write decisions.jsonl + outcomes.jsonl to DIR"
    )
    p_de_export.add_argument("directory", help="target directory")

    p_rf = sub.add_parser("reflect", help="record the outcome of a past decision")
    p_rf.add_argument(
        "decision_id", nargs="?", default=None, help="omit to list past decisions"
    )
    p_rf.add_argument("note", nargs="?", default=None, help="what actually happened")

    return parser


def workspace_list(*, service: WorkspaceService, active_name: str) -> int:
    """Print one workspace name per line; mark the active one with ``*``."""
    for ws in service.list():
        marker = "*" if ws.name == active_name else " "
        print(f"{marker} {ws.name}")
    return 0


def workspace_show(name: str | None, *, service: WorkspaceService) -> int:
    """Print the resolved workspace's name and on-disk paths."""
    ws = service.resolve(name)
    print(f"name:        {ws.name}")
    print(f"root:        {ws.root}")
    print(f"db_url:      {ws.db_url}")
    print(f"connectors:  {ws.connectors_file}")
    print(f"env:         {ws.env_file}")
    print(f"log:         {ws.log_file}")
    return 0


def prompts_list(*, service: PromptService) -> int:
    """Print one prompt name per line, with its active version."""
    for name in service.names():
        print(f"{name}  (v{service.versions(name)[-1]})")
    return 0


def prompts_show(name: str, version: int | None, *, service: PromptService) -> int:
    """Print one prompt's text (active version, or --version N)."""
    try:
        text = service.get(name) if version is None else service.read(name, version)
    except KeyError:
        print(f"no such prompt: {name}")
        return 1
    print(text)
    return 0


def prompts_diff(name: str, old: int, new: int, *, service: PromptService) -> int:
    """Print a unified diff between two versions of a prompt."""
    try:
        print(service.diff(name, old, new), end="")
    except KeyError as exc:
        print(str(exc))
        return 1
    return 0


def prompts_save(name: str, file: str, *, service: PromptService) -> int:
    """Save the contents of FILE as a new version of NAME."""
    from pathlib import Path

    text = Path(file).read_text(encoding="utf-8")
    version = service.save(name, text)
    print(f"saved {name} v{version}")
    return 0


def prompts_rollback(name: str, version: int, *, service: PromptService) -> int:
    """Re-activate an old version by appending it as the newest version."""
    try:
        new = service.rollback(name, version)
    except KeyError:
        print(f"no version {version} for {name}")
        return 1
    print(f"rolled back {name} to v{version} (now v{new})")
    return 0


async def decisions_export(directory: str, *, service) -> int:
    """Export the decision store to decisions.jsonl + outcomes.jsonl in DIR."""
    n_decisions, n_outcomes = await service.export(directory)
    print(
        f"exported {n_decisions} decision(s) and {n_outcomes} outcome(s) to {directory}"
    )
    return 0


async def reflect_list(*, service) -> int:
    """List past decisions (id + title + recommendation) for the reflect picker."""
    decisions = await service.decisions()
    if not decisions:
        print("no decisions yet — run one first with `productagents run`")
        return 0
    for d in decisions:
        print(
            f"{d.decision_id}  {d.initiative.title} — {d.recommendation.recommendation}"
        )
    return 0


async def reflect_record(decision_id: str, note: str, *, service) -> int:
    """Reflect on one past decision and persist the outcome; print the result."""
    try:
        outcome = await service.reflect_on(decision_id, note)
    except LookupError as exc:
        print(str(exc))
        return 1
    print(f"prediction accuracy: {outcome.prediction_accuracy:.0%}")
    print("actual outcomes:")
    for o in outcome.actual_outcomes or ["(none)"]:
        print(f"  • {o}")
    print("lessons learned:")
    for lesson in outcome.lessons_learned or ["(none)"]:
        print(f"  • {lesson}")
    return 1 if outcome.failed else 0


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

    if args.command is None:  # bare `productagents` → show help
        build_parser().print_help()
        return
    if args.command == "sync":
        raise SystemExit(sync_command())
    if args.command == "ipc":
        from productagents.app import ipc

        ipc.serve_stdio(workspace.name)
        return
    if args.command == "serve-ws":
        from productagents.app import devbridge

        devbridge.serve_ws(workspace.name, port=args.port)
        return
    if args.command == "workspace":
        if args.ws_command == "show":
            raise SystemExit(
                workspace_show(args.name or workspace.name, service=workspaces)
            )
        raise SystemExit(  # bare `workspace` or `workspace list`
            workspace_list(service=workspaces, active_name=workspace.name)
        )
    if args.command == "run":
        try:
            service = _build_run_service()
        except Exception as exc:
            raise SystemExit(f"cannot start run: {exc}") from exc
        if service.get(args.workflow) is None:
            raise SystemExit(f"unknown workflow: {args.workflow!r}")
        code = asyncio.run(
            run_workflow(args.workflow, args.title, args.evidence, service=service)
        )
        raise SystemExit(code)
    if args.command == "sessions":
        service = SessionService.create()
        if args.se_command == "show":
            code = asyncio.run(sessions_show(args.session_id, service=service))
            raise SystemExit(code)
        code = asyncio.run(sessions_list(service=service))
        raise SystemExit(code)
    if args.command == "prompts":
        service = PromptService.create()
        if args.pr_command == "show":
            raise SystemExit(prompts_show(args.name, args.version, service=service))
        if args.pr_command == "diff":
            raise SystemExit(
                prompts_diff(args.name, args.old, args.new, service=service)
            )
        if args.pr_command == "save":
            raise SystemExit(prompts_save(args.name, args.file, service=service))
        if args.pr_command == "rollback":
            raise SystemExit(prompts_rollback(args.name, args.version, service=service))
        raise SystemExit(prompts_list(service=service))  # bare `prompts` or `list`
    if args.command == "decisions":
        if args.de_command == "export":
            code = asyncio.run(
                decisions_export(args.directory, service=DecisionReadService.create())
            )
            raise SystemExit(code)
        raise SystemExit("usage: productagents decisions export DIR")
    if args.command == "reflect":
        if args.decision_id is None:  # list mode needs no model
            code = asyncio.run(reflect_list(service=ReflectionService.for_model(None)))
            raise SystemExit(code)
        if args.note is None:
            raise SystemExit(
                'reflect needs a note: productagents reflect <decision_id> "<note>"'
            )
        try:
            service = ReflectionService.for_model(get_model())
        except Exception as exc:  # friendly message, no traceback
            raise SystemExit(f"cannot reflect: {exc}") from exc
        code = asyncio.run(reflect_record(args.decision_id, args.note, service=service))
        raise SystemExit(code)
    raise SystemExit(f"unknown command: {args.command}")  # pragma: no cover
