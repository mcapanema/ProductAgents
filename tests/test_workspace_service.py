"""WorkspaceService — a workspace is a directory of local state (V3 Phase 4)."""

import os

from productagents.platform.workspace import (
    DEFAULT_WORKSPACE,
    Workspace,
    WorkspaceService,
)

_PATH_VARS = (
    "PRODUCTAGENTS_DB_URL",
    "PRODUCTAGENTS_CONNECTORS_FILE",
    "PRODUCTAGENTS_LOG_FILE",
)


def test_workspace_derives_artifact_paths_under_root(tmp_path):
    ws = Workspace(name="acme", root=tmp_path / "acme")
    assert ws.connectors_file == tmp_path / "acme" / "connectors.yaml"
    assert ws.env_file == tmp_path / "acme" / ".env"
    assert ws.log_file == tmp_path / "acme" / "productagents.log"
    assert ws.db_url == f"sqlite+aiosqlite:///{tmp_path / 'acme' / 'productagents.db'}"


def test_list_empty_when_home_missing(tmp_path):
    svc = WorkspaceService(home=tmp_path / "nope")
    assert svc.list() == []


def test_list_returns_workspace_directories_sorted(tmp_path):
    (tmp_path / "beta").mkdir()
    (tmp_path / "alpha").mkdir()
    (tmp_path / "a-file.txt").write_text("ignored")  # files are not workspaces
    svc = WorkspaceService(home=tmp_path)
    assert [w.name for w in svc.list()] == ["alpha", "beta"]


def test_get_returns_workspace_only_when_dir_exists(tmp_path):
    (tmp_path / "acme").mkdir()
    svc = WorkspaceService(home=tmp_path)
    got = svc.get("acme")
    assert got is not None
    assert got.root == tmp_path / "acme"
    assert svc.get("missing") is None


def test_resolve_defaults_to_default_workspace_and_creates_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_WORKSPACE", raising=False)
    svc = WorkspaceService(home=tmp_path)
    ws = svc.resolve()
    assert ws.name == DEFAULT_WORKSPACE
    assert ws.root.is_dir()


def test_resolve_honors_env_workspace_name(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_WORKSPACE", "team-x")
    svc = WorkspaceService(home=tmp_path)
    ws = svc.resolve()
    assert ws.name == "team-x"
    assert ws.root == tmp_path / "team-x"


def test_resolve_explicit_name_overrides_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_WORKSPACE", "team-x")
    svc = WorkspaceService(home=tmp_path)
    assert svc.resolve("override").name == "override"


def test_activate_sets_path_env_vars(tmp_path, monkeypatch):
    for var in _PATH_VARS:
        monkeypatch.delenv(var, raising=False)
    ws = Workspace(name="acme", root=tmp_path / "acme")
    WorkspaceService(home=tmp_path).activate(ws)
    assert os.environ["PRODUCTAGENTS_DB_URL"] == ws.db_url
    assert os.environ["PRODUCTAGENTS_CONNECTORS_FILE"] == str(ws.connectors_file)
    assert os.environ["PRODUCTAGENTS_LOG_FILE"] == str(ws.log_file)


def test_activate_does_not_override_explicit_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DB_URL", "postgresql+asyncpg://explicit/db")
    ws = Workspace(name="acme", root=tmp_path / "acme")
    WorkspaceService(home=tmp_path).activate(ws)
    assert os.environ["PRODUCTAGENTS_DB_URL"] == "postgresql+asyncpg://explicit/db"


def test_activate_loads_workspace_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("WS_SECRET", raising=False)
    root = tmp_path / "acme"
    root.mkdir()
    (root / ".env").write_text("WS_SECRET=from-workspace\n")
    WorkspaceService(home=tmp_path).activate(Workspace(name="acme", root=root))
    assert os.environ["WS_SECRET"] == "from-workspace"


def test_workspace_exposes_prompts_dir(tmp_path):
    ws = Workspace(name="w", root=tmp_path)
    assert ws.prompts_dir == tmp_path / "prompts"


def test_activate_points_prompts_dir_env_at_workspace(monkeypatch, tmp_path):
    monkeypatch.delenv("PRODUCTAGENTS_PROMPTS_DIR", raising=False)
    ws = Workspace(name="w", root=tmp_path)
    WorkspaceService(tmp_path.parent).activate(ws)
    assert os.environ["PRODUCTAGENTS_PROMPTS_DIR"] == str(tmp_path / "prompts")
