"""PyInstaller entry point for the bundled IPC sidecar.

The packaged Tauri app spawns this frozen binary instead of `uv run
productagents ipc`. It just runs the existing CLI with the `ipc` subcommand, so
workspace resolution / activation / logging stay identical to the dev path. No
argv parsing here — the binary is the IPC server, nothing else.
"""

from __future__ import annotations

from productagents.app import cli


def run() -> None:
    cli.main(["ipc"])


if __name__ == "__main__":
    run()
