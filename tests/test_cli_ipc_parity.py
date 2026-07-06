"""GUI-CLI parity gate: every GUI (IPC) operation must be reachable from the CLI.

The desktop GUI talks to the platform only through the IPC dispatch table in
``productagents.app.ipc.handle``. This test maps every IPC method to the CLI
invocation that performs the same Application-Service operation — so adding an
IPC method without a CLI counterpart (or a justified exemption) fails CI.
See root CLAUDE.md, "GUI-CLI parity".
"""

import inspect
import re

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

# GUI-only surface, deliberately not mirrored in the CLI — each needs a reason.
EXEMPT = {
    "run.cancel": "Ctrl-C interrupts a streaming CLI run",
    "preferences.get": "GUI theme — pure presentation state, no platform effect",
    "preferences.set": "GUI theme — pure presentation state, no platform effect",
}


def _ipc_methods() -> set[str]:
    # ponytail: regex over the dispatch-table source (keys are dotted strings
    # mapped to _-prefixed closures); hoist a module-level method registry in
    # ipc.py if the table ever stops being a dict literal inside handle().
    source = inspect.getsource(ipc.handle)
    methods = set(re.findall(r'"([a-z_]+(?:\.[a-z_]+)+)":\s*_', source))
    methods.add("run")  # the explicit streaming branch above the table
    assert len(methods) > 20, "regex no longer finds the ipc dispatch table"
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


def test_every_parity_argv_parses():
    parser = cli.build_parser()
    for method, argv in PARITY.items():
        try:
            parser.parse_args(argv)
        except SystemExit as exc:  # argparse exits on unknown args
            raise AssertionError(
                f"CLI lost the command for ipc method {method!r}: {argv}"
            ) from exc
