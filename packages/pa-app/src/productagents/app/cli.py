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
import json
import logging

from productagents.core.config import load_env
from productagents.core.logging_config import configure_logging
from productagents.core.models import Initiative
from productagents.platform import events as ev
from productagents.platform.bootstrap import bootstrap_home
from productagents.platform.configuration import ConfigurationService
from productagents.platform.connector_service import ConnectorService
from productagents.platform.connectors import describe_report, run_connector_sync
from productagents.platform.context import make_recorder
from productagents.platform.decision_read_service import DecisionReadService
from productagents.platform.llm import get_model
from productagents.platform.memory_service import MemoryService
from productagents.platform.prompt_service import PromptService
from productagents.platform.reflection_service import ReflectionService
from productagents.platform.session_service import SessionService
from productagents.platform.workflow import WorkflowService
from productagents.platform.workspace import WorkspaceError, WorkspaceService

logger = logging.getLogger(__name__)


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


def _build_run_service(
    *, human_in_the_loop: bool = False, workspace: str = "default"
) -> WorkflowService:
    """Production WorkflowService for runs: real model + DB recorder.

    ``human_in_the_loop`` is False for the headless CLI ``run`` (governance stays
    advisory and the run completes). The IPC adapter builds it ``True`` so a GUI
    run can pause for approval; with no approver the graph still auto-approves.
    """
    model = get_model()
    return WorkflowService.for_model(
        model,
        recorder=make_recorder(workspace=workspace),
        human_in_the_loop=human_in_the_loop,
        workspace=workspace,
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
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "override a workspace setting for this invocation only "
            "(repeatable; e.g. --set debate_rounds=3). Outranks env and DB."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    p_sync = sub.add_parser("sync", help="run one connector sync and exit")
    p_sync.add_argument(
        "--connector", default=None, help="scope the sync to one connector"
    )
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

    p_wf = sub.add_parser("workflows", help="list registered workflows")
    wf_sub = p_wf.add_subparsers(dest="wf_command")
    wf_sub.add_parser("list", help="list workflows")
    p_wf_show = wf_sub.add_parser("show", help="show one workflow + its topology")
    p_wf_show.add_argument("name")

    p_co = sub.add_parser("connectors", help="list, probe, or configure connectors")
    co_sub = p_co.add_subparsers(dest="co_command")
    co_sub.add_parser("list", help="configured connectors + last-synced times")
    p_co_health = co_sub.add_parser(
        "health", help="readiness probe (exit 1 on failure)"
    )
    p_co_health.add_argument("name", nargs="?", default=None, help="one connector key")
    p_co_cfg = co_sub.add_parser(
        "config",
        help="show connector config blocks, or save one: config NAME KEY=VALUE...",
    )
    p_co_cfg.add_argument("connector", nargs="?", default=None)
    p_co_cfg.add_argument("pairs", nargs="*", metavar="KEY=VALUE")
    p_co_cfg.add_argument(
        "--secret",
        action="append",
        default=[],
        metavar="VAR=VALUE",
        help="secret env var referenced by a *_env field (written to .env, repeatable)",
    )

    p_ws = sub.add_parser("workspace", help="list or show workspaces")
    ws_sub = p_ws.add_subparsers(dest="ws_command")
    ws_sub.add_parser("list", help="list workspaces")
    p_ws_create = ws_sub.add_parser("create", help="create a new workspace")
    p_ws_create.add_argument("name")
    p_ws_use = ws_sub.add_parser("use", help="set the active workspace")
    p_ws_use.add_argument("name")
    p_ws_rename = ws_sub.add_parser(
        "rename", help="rename a workspace (moves all of its data)"
    )
    p_ws_rename.add_argument("old")
    p_ws_rename.add_argument("new")
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

    p_de = sub.add_parser("decisions", help="list, show, or export recorded decisions")
    de_sub = p_de.add_subparsers(dest="de_command")
    de_sub.add_parser("list", help="list recorded decisions")
    p_de_show = de_sub.add_parser("show", help="dump one decision + outcomes as JSON")
    p_de_show.add_argument("decision_id")
    p_de_export = de_sub.add_parser(
        "export", help="write decisions.jsonl + outcomes.jsonl to DIR"
    )
    p_de_export.add_argument("directory", help="target directory")

    p_rf = sub.add_parser("reflect", help="record the outcome of a past decision")
    p_rf.add_argument(
        "decision_id", nargs="?", default=None, help="omit to list past decisions"
    )
    p_rf.add_argument("note", nargs="?", default=None, help="what actually happened")

    p_me = sub.add_parser("memory", help="browse organizational memory")
    me_sub = p_me.add_subparsers(dest="me_command")
    me_sub.add_parser("lessons", help="list the lesson corpus (newest first)")

    p_cf = sub.add_parser("config", help="show or persist workspace configuration")
    cf_sub = p_cf.add_subparsers(dest="cf_command")
    cf_sub.add_parser("show", help="model/provider/key status + tunables with origins")
    p_cf_set = cf_sub.add_parser(
        "set", help="persist model/provider/api-key/tunables (unlike --set)"
    )
    p_cf_set.add_argument("--model", default=None, help="provider-prefixed model id")
    p_cf_set.add_argument("--provider", default=None)
    p_cf_set.add_argument(
        "--api-key", dest="api_key", default=None, help="written to the workspace .env"
    )
    p_cf_set.add_argument("pairs", nargs="*", metavar="KEY=VALUE")

    return parser


async def workspace_list(*, service: WorkspaceService, active_name: str) -> int:
    """Print one workspace name per line; mark the active one with ``*``."""
    for row in await service.list():
        marker = "*" if row["name"] == active_name else " "
        print(f"{marker} {row['name']}")
    return 0


async def workspace_show(
    name: str | None, *, service: WorkspaceService, active_name: str
) -> int:
    """Print the resolved workspace's name and the shared home's paths."""
    name = name or active_name
    row = await service.get(name)
    if row is None:
        print(f"no such workspace: {name}")
        return 1
    home = service.home()
    print(f"name:        {row['name']}")
    print(f"active:      {'yes' if name == active_name else 'no'}")
    print(f"created_at:  {row['created_at']}")
    print(f"home:        {home.root}")
    print(f"db_url:      {home.db_url}")
    print(f"connectors:  {home.connectors_file}")
    print(f"env:         {home.env_file}")
    print(f"log:         {home.log_file}")
    print(f"prompts:     {service.prompts_dir(name)}")
    return 0


async def workspace_create(name: str, *, service: WorkspaceService) -> int:
    """Create a new workspace; print its name."""
    try:
        row = await service.create(name)
    except WorkspaceError as exc:
        print(str(exc))
        return 1
    print(f"created workspace {row['name']}")
    return 0


async def workspace_use(name: str, *, service: WorkspaceService) -> int:
    """Persist NAME as the active workspace for future invocations."""
    try:
        await service.set_active(name)
    except WorkspaceError as exc:
        print(f"{exc} — create it with `productagents workspace create {name}`")
        return 1
    print(f"active workspace: {name}")
    return 0


async def workspace_rename(old: str, new: str, *, service: WorkspaceService) -> int:
    """Rename a workspace; all of its scoped data moves with it."""
    try:
        await service.rename(old, new)
    except WorkspaceError as exc:
        print(str(exc))
        return 1
    print(f"renamed workspace {old} → {new}")
    return 0


def workflows_list(*, service: WorkflowService) -> int:
    """Print one registered workflow per line (name + title)."""
    for w in service.list():
        print(f"{w.name}  {w.title}")
    return 0


def workflows_show(name: str, *, service: WorkflowService) -> int:
    """Print one workflow's metadata and, when exposed, its graph topology."""
    w = service.get(name)
    if w is None:
        print(f"no such workflow: {name}")
        return 1
    print(f"name:        {w.name}")
    print(f"title:       {w.title}")
    print(f"description: {w.description}")
    topo = w.topology() if w.topology is not None else None
    if topo:
        print("nodes:")
        for node in topo["nodes"]:
            print(f"  {node['id']}")
        print("edges:")
        for edge in topo["edges"]:
            arrow = "-?->" if edge.get("conditional") else "--->"
            print(f"  {edge['source']} {arrow} {edge['target']}")
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


async def decisions_list(*, service) -> int:
    """Print one recorded decision per line (id, title, recommendation)."""
    rows = await service.list()
    if not rows:
        print("no decisions yet — run one first with `productagents run`")
        return 0
    for d in rows:
        rec = d.recommendation
        print(
            f"{d.decision_id}  {d.initiative.title} — "
            f"{rec.recommendation} ({rec.confidence:.0%})"
        )
    return 0


async def decisions_show(decision_id: str, *, service) -> int:
    """Dump one decision record + its reflected outcomes as JSON."""
    record, outcomes = await service.get(decision_id)
    if record is None:
        print(f"no such decision: {decision_id}")
        return 1
    print(record.model_dump_json(indent=2))
    for o in outcomes:
        print(o.model_dump_json(indent=2))
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


async def memory_lessons(*, service) -> int:
    """Print the organizational-memory lesson corpus (✓ = validated by reflection)."""
    lessons = await service.lessons()
    if not lessons:
        print("no lessons yet — run and reflect on a decision first")
        return 0
    for lesson in lessons:
        mark = "✓" if lesson.validated else "·"
        accuracy = (
            f" ({lesson.prediction_accuracy:.0%})"
            if lesson.prediction_accuracy is not None
            else ""
        )
        print(f"{mark} [{lesson.decision_id}] {lesson.title}{accuracy}: {lesson.text}")
    return 0


async def connectors_list(*, service) -> int:
    """Print each configured connector with its last successful-sync time."""
    plan = await service.plan()
    last = await service.last_synced()
    if not plan.configs:
        print("no connectors configured")
    for name in sorted(plan.configs):
        print(f"{name}  last synced: {last.get(name, 'never')}")
    for problem in plan.problems:
        print(f"⚠ {problem}")
    return 0


async def connectors_health(name: str | None, *, service) -> int:
    """Probe connector readiness (all, or just NAME). Exit 1 on any failure."""
    report = await service.health(connector=name)
    for key, status in report.statuses.items():
        mark = "✓" if status.ok else "✗"
        print(f"{mark} {key}: {status.detail}")
    for problem in report.problems:
        print(f"⚠ {problem}")
    failed = any(not s.ok for s in report.statuses.values()) or bool(report.problems)
    return 1 if failed else 0


def _parse_typed_pairs(pairs: list[str]) -> dict:
    """Parse KEY=VALUE pairs; values JSON-decode when possible (true, 5, 1.5)."""
    out: dict = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise SystemExit(f"expected KEY=VALUE, got {pair!r}")
        try:
            out[key] = json.loads(value)
        except json.JSONDecodeError:
            out[key] = value  # bare strings stay strings
    return out


async def connectors_config_list(*, service) -> int:
    """Print every connector's DB-backed config block (secrets are env names only)."""
    for entry in await service.config_list():
        state = "installed" if entry["installed"] else "not installed"
        print(f"{entry['connector']}  ({state})")
        for key, value in entry["config"].items():
            print(f"  {key}: {value}")
        for problem in entry["problems"]:
            print(f"  ⚠ {problem}")
    return 0


async def connectors_config_save(
    connector: str, pairs: list[str], secret_pairs: list[str], *, service
) -> int:
    """Validate-then-write one connector's config block; secrets go to .env."""
    config = _parse_typed_pairs(pairs)
    secrets: dict[str, str] = {}
    for pair in secret_pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise SystemExit(f"expected VAR=VALUE, got {pair!r}")
        secrets[key] = value  # verbatim — a secret is never JSON-coerced
    try:
        entry = await service.config_save(connector, config, secrets=secrets or None)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"saved {entry['connector']}")
    for problem in entry["problems"]:
        print(f"⚠ {problem}")
    return 1 if entry["problems"] else 0


def sync_command(*, only: str | None = None, syncer=run_connector_sync) -> int:
    """Run one connector sync headlessly, print the report, return an exit code.

    For cron/launchd: ``productagents sync [--connector NAME]``. Returns 1 if any
    connector failed or the config had problems so the scheduler/CI surfaces it.
    ponytail: print (not the file logger) because no TUI owns the terminal here.
    """
    report = asyncio.run(syncer(only=only))
    print(describe_report(report))
    failed = any(not r.ok for r in report.results) or bool(report.problems)
    return 1 if failed else 0


def config_show(*, service) -> int:
    """Print model/provider/key readiness plus each tunable with its origin."""
    status = service.status()
    print(f"model:     {status.model or '(not set)'}")
    print(f"provider:  {status.provider or '(auto)'}")
    key_state = "present" if status.key_present else "MISSING"
    print(f"api key:   {status.key_var or '(none)'} [{key_state}]")
    origins = service.settings_origins()
    for key, value in service.settings().items():
        print(f"{key}: {value}  ({origins.get(key, 'default')})")
    for problem in status.problems:
        print(f"⚠ {problem}")
    return 0


async def config_set_cmd(
    model: str | None,
    provider: str | None,
    api_key: str | None,
    pairs: list[str],
    *,
    service,
) -> int:
    """Persist workspace config (model/provider to DB, api key to .env).

    The persisted counterpart of the per-invocation ``--set`` flag. KEY names are
    validated against the service's tunables so a typo can't silently no-op.
    """
    settings = parse_set_overrides(pairs)
    unknown = set(settings) - set(service.settings())
    if unknown:
        print(f"unknown setting(s): {', '.join(sorted(unknown))}")
        return 1
    model = model or service.status().model
    if not model:
        print("no model configured yet — pass --model")
        return 1
    await service.set(model, provider=provider, api_key=api_key, settings=settings)
    return config_show(service=service)


def parse_set_overrides(pairs: list[str]) -> dict[str, str]:
    """Parse repeated ``--set KEY=VALUE`` pairs; exit with a friendly message."""
    overrides: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise SystemExit(f"--set expects KEY=VALUE, got {pair!r}")
        overrides[key.strip()] = value
    return overrides


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    workspaces = WorkspaceService()
    workspaces.activate()
    load_env()
    try:
        active = workspaces.resolve(args.workspace)
    except WorkspaceError as exc:
        raise SystemExit(str(exc)) from exc

    config = ConfigurationService(active_name=active)
    try:
        config.apply_overrides(parse_set_overrides(args.overrides))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    async def _startup() -> None:
        # bootstrap_home and config.load() share this one run because the
        # process-wide engine is loop-bound once created (its asyncpg/aiosqlite
        # objects can't cross asyncio.run() calls). That alone does NOT satisfy
        # the single-loop constraint for the whole process — every command below
        # calls asyncio.run() again in its own fresh loop and may reuse the same
        # cached engine. The dispose() below is what makes that safe.
        await bootstrap_home(workspaces.home())
        try:
            await config.load()  # workspace DB -> env (precedence: see the service)
        except Exception:
            # degrade, never crash: env/defaults still work, origins just won't show db
            logger.error(
                "workspace config load failed; continuing without it", exc_info=True
            )
        from productagents.platform.context import get_engine

        # ponytail: dispose empties the loop-bound connection pool so later
        # asyncio.run() loops start clean — required for asyncpg (loop-bound
        # connections), harmless for aiosqlite. dispose() does not destroy the
        # engine object; a later command re-creates pooled connections lazily.
        await get_engine().dispose()

    # env vars it reads are set by activate() above, not by _startup
    configure_logging()
    asyncio.run(_startup())

    if args.command is None:  # bare `productagents` → show help
        build_parser().print_help()
        return
    if args.command == "sync":
        raise SystemExit(sync_command(only=args.connector))
    if args.command == "ipc":
        from productagents.app import ipc

        ipc.serve_stdio(active, config=config)
        return
    if args.command == "serve-ws":
        from productagents.app import devbridge

        devbridge.serve_ws(active, port=args.port, config=config)
        return
    if args.command == "workspace":
        if args.ws_command == "create":
            raise SystemExit(
                asyncio.run(workspace_create(args.name, service=workspaces))
            )
        if args.ws_command == "use":
            raise SystemExit(asyncio.run(workspace_use(args.name, service=workspaces)))
        if args.ws_command == "rename":
            raise SystemExit(
                asyncio.run(workspace_rename(args.old, args.new, service=workspaces))
            )
        if args.ws_command == "show":
            raise SystemExit(
                asyncio.run(
                    workspace_show(args.name, service=workspaces, active_name=active)
                )
            )
        raise SystemExit(  # bare `workspace` or `workspace list`
            asyncio.run(workspace_list(service=workspaces, active_name=active))
        )
    if args.command == "workflows":
        service = WorkflowService.for_model(None, workspace=active)
        if args.wf_command == "show":
            raise SystemExit(workflows_show(args.name, service=service))
        raise SystemExit(workflows_list(service=service))  # bare `workflows` or `list`
    if args.command == "connectors":
        service = ConnectorService(workspace=active)
        if args.co_command == "health":
            code = asyncio.run(connectors_health(args.name, service=service))
            raise SystemExit(code)
        if args.co_command == "config":
            if args.connector is None:
                code = asyncio.run(connectors_config_list(service=service))
                raise SystemExit(code)
            code = asyncio.run(
                connectors_config_save(
                    args.connector, args.pairs, args.secret, service=service
                )
            )
            raise SystemExit(code)
        raise SystemExit(  # bare `connectors` or `connectors list`
            asyncio.run(connectors_list(service=service))
        )
    if args.command == "run":
        try:
            service = _build_run_service(workspace=active)
        except Exception as exc:
            raise SystemExit(f"cannot start run: {exc}") from exc
        if service.get(args.workflow) is None:
            raise SystemExit(f"unknown workflow: {args.workflow!r}")
        code = asyncio.run(
            run_workflow(args.workflow, args.title, args.evidence, service=service)
        )
        raise SystemExit(code)
    if args.command == "sessions":
        service = SessionService.create(active)
        if args.se_command == "show":
            code = asyncio.run(sessions_show(args.session_id, service=service))
            raise SystemExit(code)
        code = asyncio.run(sessions_list(service=service))
        raise SystemExit(code)
    if args.command == "prompts":
        service = PromptService.create(active)
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
        service = DecisionReadService.create(active)
        if args.de_command == "export":
            code = asyncio.run(decisions_export(args.directory, service=service))
            raise SystemExit(code)
        if args.de_command == "show":
            code = asyncio.run(decisions_show(args.decision_id, service=service))
            raise SystemExit(code)
        raise SystemExit(  # bare `decisions` or `decisions list`
            asyncio.run(decisions_list(service=service))
        )
    if args.command == "config":
        if args.cf_command == "set":
            code = asyncio.run(
                config_set_cmd(
                    args.model, args.provider, args.api_key, args.pairs, service=config
                )
            )
            raise SystemExit(code)
        raise SystemExit(config_show(service=config))  # bare `config` or `show`
    if args.command == "reflect":
        if args.decision_id is None:  # list mode needs no model
            code = asyncio.run(
                reflect_list(
                    service=ReflectionService.for_model(None, workspace=active)
                )
            )
            raise SystemExit(code)
        if args.note is None:
            raise SystemExit(
                'reflect needs a note: productagents reflect <decision_id> "<note>"'
            )
        try:
            service = ReflectionService.for_model(get_model(), workspace=active)
        except Exception as exc:  # friendly message, no traceback
            raise SystemExit(f"cannot reflect: {exc}") from exc
        code = asyncio.run(reflect_record(args.decision_id, args.note, service=service))
        raise SystemExit(code)
    if args.command == "memory":
        service = MemoryService.create(active)
        raise SystemExit(asyncio.run(memory_lessons(service=service)))
    raise SystemExit(f"unknown command: {args.command}")  # pragma: no cover
