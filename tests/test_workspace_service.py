"""WorkspaceService — workspaces are logical scopes over one shared home."""

import os

import pytest

from productagents.knowledge.repositories.sqlmodel.engine import make_engine
from productagents.memory.store import create_all
from productagents.platform.workspace import (
    DEFAULT_WORKSPACE,
    SharedHome,
    WorkspaceError,
    WorkspaceService,
    default_home,
)


@pytest.fixture
async def svc(tmp_path):
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    await create_all(engine)
    return WorkspaceService(home=SharedHome(root=tmp_path), engine=engine)


def test_shared_home_paths(tmp_path):
    home = SharedHome(root=tmp_path)
    assert home.db_url == f"sqlite+aiosqlite:///{tmp_path / 'productagents.db'}"
    assert home.env_file == tmp_path / ".env"
    assert home.log_file == tmp_path / "productagents.log"
    assert home.prompts_root == tmp_path / "prompts"
    assert home.active_file == tmp_path / ".active"
    assert home.legacy_workspaces_dir == tmp_path / "workspaces"


def test_default_home_no_longer_appends_workspaces(monkeypatch, tmp_path):
    monkeypatch.setenv("PRODUCTAGENTS_HOME", str(tmp_path))
    assert default_home().root == tmp_path


async def test_create_list_get_roundtrip(svc):
    created = await svc.create("acme")
    assert created["name"] == "acme"
    assert [w["name"] for w in await svc.list()] == ["acme"]
    assert (await svc.get("acme"))["name"] == "acme"
    assert await svc.get("nope") is None


async def test_create_rejects_invalid_and_duplicate(svc):
    for bad in ("", ".hidden", "a/b", "a b", "..", "x" * 65):
        with pytest.raises(WorkspaceError):
            await svc.create(bad)
    await svc.create("acme")
    with pytest.raises(WorkspaceError):
        await svc.create("acme")


async def test_set_active_requires_row_and_persists_marker(svc, monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_WORKSPACE", raising=False)
    with pytest.raises(WorkspaceError):
        await svc.set_active("nope")
    with pytest.raises(WorkspaceError):
        await svc.set_active("..")
    await svc.create("acme")
    await svc.set_active("acme")
    assert svc.active_name() == "acme"
    assert svc.resolve() == "acme"


def test_resolve_precedence_and_validation(svc, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_WORKSPACE", "team-x")
    assert svc.resolve() == "team-x"
    assert svc.resolve("explicit") == "explicit"
    with pytest.raises(WorkspaceError):
        svc.resolve("../evil")
    monkeypatch.delenv("PRODUCTAGENTS_WORKSPACE")
    assert svc.resolve() == DEFAULT_WORKSPACE  # no marker written yet


async def test_ensure_default_is_idempotent(svc):
    await svc.ensure_default()
    await svc.ensure_default()
    assert [w["name"] for w in await svc.list()] == [DEFAULT_WORKSPACE]


def test_activate_points_env_at_shared_paths(tmp_path, monkeypatch):
    for var in (
        "PRODUCTAGENTS_DB_URL",
        "PRODUCTAGENTS_CONNECTORS_FILE",
        "PRODUCTAGENTS_LOG_FILE",
        "PRODUCTAGENTS_PROMPTS_DIR",
    ):
        monkeypatch.delenv(var, raising=False)
    home = SharedHome(root=tmp_path)
    (tmp_path / ".env").write_text("WS_SHARED_SECRET=s3\n")
    monkeypatch.delenv("WS_SHARED_SECRET", raising=False)
    WorkspaceService(home=home).activate()
    assert os.environ["PRODUCTAGENTS_DB_URL"] == home.db_url
    assert os.environ["PRODUCTAGENTS_LOG_FILE"] == str(home.log_file)
    assert os.environ["PRODUCTAGENTS_PROMPTS_DIR"] == str(home.prompts_root)
    assert os.environ["WS_SHARED_SECRET"] == "s3"


def test_prompts_dir_is_per_workspace_subdir(tmp_path):
    svc = WorkspaceService(home=SharedHome(root=tmp_path))
    assert svc.prompts_dir("acme") == tmp_path / "prompts" / "acme"
