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
from productagents.platform.connectors import describe_report, run_connector_sync
from productagents.platform.workspace import WorkspaceService


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
    raise SystemExit(f"unknown command: {args.command}")  # pragma: no cover
