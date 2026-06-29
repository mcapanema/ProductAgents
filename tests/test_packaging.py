"""Phase 8e packaging seams: sidecar entry + no-key resilience + version sync."""

from __future__ import annotations

import productagents.app._sidecar_main as sidecar_main
import productagents.app.ipc as ipc


def test_sidecar_entry_runs_ipc(monkeypatch):
    """The frozen entry runs the `ipc` subcommand with no argv parsing."""
    seen: list[list[str]] = []
    monkeypatch.setattr("productagents.app.cli.main", lambda argv: seen.append(argv))
    sidecar_main.run()
    assert seen == [["ipc"]]


def test_build_workflows_survives_missing_model(monkeypatch):
    """A fresh install has no API key; the sidecar must still start so the GUI
    can reach Settings. get_model() failing must not crash build_workflows."""

    def boom(*_a, **_k):
        raise RuntimeError("no api key configured")

    monkeypatch.setattr("productagents.app.cli.get_model", boom)
    service = ipc._build_workflows(human_in_the_loop=True)
    # list() reads the registered workflow names; it needs no model.
    assert any(w.name == "evaluate_initiative" for w in service.list())
