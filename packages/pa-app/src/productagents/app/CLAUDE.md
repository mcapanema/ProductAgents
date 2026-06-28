# app/ — presentation adapters

`productagents.app` is the presentation layer. It is a **thin client of the
`productagents.platform` Application Services**: it imports only `platform.*`,
`core.*`, and sibling `app.*` modules — never `agents`, `memory`, `knowledge`,
or `connectors`.

## Adapters

| Module | Role |
| --- | --- |
| `cli.py` | The command-line client and the `productagents` console entry point (`main`). Parses args with stdlib `argparse` and dispatches to platform services. No subcommand → `launch_tui`. Subcommands: `run`, `sync`, `workspace list/show`, `sessions list/show`. |
| `tui/` | The Textual GUI (see `tui/CLAUDE.md`). `launch_tui(workspace_name)` builds and runs the app; `_build_app` is the composition root. |
| `setup.py` | `check_config` / `write_env` readiness + `.env` writer, shared by both adapters. |

## CLI contract

`main(argv=None)` always: resolve workspace (`WorkspaceService().resolve(--workspace)`)
→ `activate` → `load_env` → `configure_logging` → dispatch. Every command handler
returns an `int` exit code; `main` raises `SystemExit(code)`. Handlers take their
collaborating service via a keyword arg so they test headless (see
`tests/test_cli.py`) — no command builds a real model or hits the network in tests.

- `run WORKFLOW TITLE [--evidence SPEC]` builds a real `WorkflowService`
  (`human_in_the_loop=False`) and streams events through `render_event`. Exit 1
  on a `SessionFailed`.
- `render_event(event)` is the pure text mirror of the TUI's per-event panel
  routing — one line per event, `None` to skip.
- `workspace`/`sessions` with no sub-action default to `list`.
