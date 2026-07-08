"""GUI-CLI parity gate: every GUI (IPC) operation must be reachable from the CLI.

The desktop GUI talks to the platform only through the IPC dispatch table in
``productagents.app.ipc.handle``. This test maps every IPC method to the CLI
invocation that performs the same Application-Service operation — so adding an
IPC method without a CLI counterpart (or a justified exemption) fails CI.
See root CLAUDE.md, "GUI-CLI parity".
"""

import inspect

from productagents.app import cli, ipc

# ipc method -> a CLI argv that performs the same operation (must parse).
PARITY = {
    "run": ["run", "evaluate_initiative", "t", "--approve"],
    "workflows.list": ["workflows", "list"],
    "workflows.show": ["workflows", "show", "evaluate_initiative"],
    "workspaces.list": ["workspace", "list"],
    "workspaces.show": ["workspace", "show"],
    "workspaces.create": ["workspace", "create", "w"],
    "workspaces.use": ["workspace", "use", "w"],
    "workspaces.rename": ["workspace", "rename", "old", "new"],
    "sessions.list": ["sessions", "list"],
    "sessions.show": ["sessions", "show", "s1"],
    "decisions.list": ["decisions", "list"],
    "decisions.show": ["decisions", "show", "d1"],
    "connectors.list": ["connectors", "list"],
    "connectors.health": ["connectors", "health", "github"],
    "connectors.sync": ["sync", "--connector", "github"],
    "connectors.config.list": ["connectors", "config"],
    "connectors.config.save": [
        "connectors",
        "config",
        "github",
        "enabled=true",
        "--secret",
        "T=x",
    ],
    "prompts.list": ["prompts", "list"],
    "prompts.show": ["prompts", "show", "judge"],
    "prompts.diff": ["prompts", "diff", "judge", "0", "1"],
    "prompts.save": ["prompts", "save", "judge", "f.txt"],
    "prompts.rollback": ["prompts", "rollback", "judge", "1"],
    "config.get": ["config", "show"],
    "config.set": ["config", "set", "--model", "anthropic:claude-sonnet-4-6"],
    "reflection.record": ["reflect", "d1", "note"],
    "memory.lessons": ["memory", "lessons"],
}

# Each PARITY method's argv must resolve to this CLI handler
# (parse_args(argv).func.__name__). connectors.config.{list,save} share the
# p_co_cfg subparser, so both resolve to the one connectors_config dispatcher.
HANDLERS = {
    "run": "run_workflow",
    "workflows.list": "workflows_list",
    "workflows.show": "workflows_show",
    "workspaces.list": "workspace_list",
    "workspaces.show": "workspace_show",
    "workspaces.create": "workspace_create",
    "workspaces.use": "workspace_use",
    "workspaces.rename": "workspace_rename",
    "sessions.list": "sessions_list",
    "sessions.show": "sessions_show",
    "decisions.list": "decisions_list",
    "decisions.show": "decisions_show",
    "connectors.list": "connectors_list",
    "connectors.health": "connectors_health",
    "connectors.sync": "sync_command",
    "connectors.config.list": "connectors_config",
    "connectors.config.save": "connectors_config",
    "prompts.list": "prompts_list",
    "prompts.show": "prompts_show",
    "prompts.diff": "prompts_diff",
    "prompts.save": "prompts_save",
    "prompts.rollback": "prompts_rollback",
    "config.get": "config_show",
    "config.set": "config_set_cmd",
    "reflection.record": "reflect_record",
    "memory.lessons": "memory_lessons",
}

# GUI-only surface, deliberately not mirrored in the CLI — each needs a reason.
EXEMPT = {
    "run.cancel": "Ctrl-C interrupts a streaming CLI run",
    "preferences.get": "GUI theme — pure presentation state, no platform effect",
    "preferences.set": "GUI theme — pure presentation state, no platform effect",
}


def _ipc_methods() -> set[str]:
    # The dispatch table is a module constant; read its keys directly. "run" is
    # the explicit streaming branch in handle(), above the table.
    methods = set(ipc.DISPATCH)
    methods.add("run")
    assert len(methods) > 20, "the ipc dispatch table shrank unexpectedly"
    return methods


def test_every_ipc_method_is_mapped_or_exempt():
    methods = _ipc_methods()
    mapped = set(PARITY) | set(EXEMPT)
    assert methods == mapped, (
        f"IPC methods with no CLI mapping (add the subcommand + PARITY entry, "
        f"or an EXEMPT reason): {sorted(methods - mapped)}; "
        f"stale entries for removed methods: {sorted(mapped - methods)}"
    )


def test_no_method_is_both_mapped_and_exempt():
    assert not set(PARITY) & set(EXEMPT)


def test_every_parity_argv_routes_to_its_handler():
    parser = cli.build_parser()
    assert set(HANDLERS) == set(PARITY), (
        "HANDLERS must stay 1:1 with PARITY: "
        f"missing {sorted(set(PARITY) - set(HANDLERS))}, "
        f"stale {sorted(set(HANDLERS) - set(PARITY))}"
    )
    main_src = inspect.getsource(cli.main)
    for method, argv in PARITY.items():
        try:
            ns = parser.parse_args(argv)
        except SystemExit as exc:  # argparse exits on unknown args
            raise AssertionError(
                f"CLI lost the command for ipc method {method!r}: {argv}"
            ) from exc
        func = getattr(ns, "func", None)
        assert func is not None, (
            f"ipc method {method!r} argv {argv} parsed to a subparser with no "
            f"handler (missing set_defaults(func=...) in build_parser)"
        )
        assert func.__name__ == HANDLERS[method], (
            f"ipc method {method!r} argv {argv} routes to {func.__name__!r}, "
            f"expected {HANDLERS[method]!r}"
        )
        assert HANDLERS[method] in main_src, (
            f"handler {HANDLERS[method]!r} for {method!r} is not dispatched in "
            f"main() — the func marker has drifted from real dispatch"
        )
