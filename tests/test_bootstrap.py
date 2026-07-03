"""Adopt+upgrade bootstrap: one-time adoption of the legacy default workspace DB."""

import sqlite3

from productagents.knowledge.repositories.sqlmodel.engine import make_engine
from productagents.platform.bootstrap import bootstrap_home
from productagents.platform.workspace import SharedHome, WorkspaceService


def _make_legacy_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE memory_decision (decision_id TEXT PRIMARY KEY,"
        " initiative_title TEXT, payload JSON, embedding JSON, created_at TEXT)"
    )
    con.execute(
        "INSERT INTO memory_decision VALUES ('d1', 't', '{}', '[]', '2026-01-01')"
    )
    con.execute(
        "CREATE TABLE workspace_config (key TEXT PRIMARY KEY, value TEXT,"
        " updated_at TEXT)"
    )
    con.execute("INSERT INTO workspace_config VALUES ('model', 'anthropic:m', 't')")
    con.commit()
    con.close()


async def test_adopts_legacy_default_db(tmp_path):
    home = SharedHome(root=tmp_path)
    legacy = home.legacy_workspaces_dir / "default" / "productagents.db"
    _make_legacy_db(legacy)
    (legacy.parent / ".env").write_text("ANTHROPIC_API_KEY=k\n")

    engine = make_engine(home.db_url)
    await bootstrap_home(home, engine=engine)

    con = sqlite3.connect(home.db_path)
    rows = con.execute("SELECT decision_id, workspace FROM memory_decision").fetchall()
    assert rows == [("d1", "default")]
    cfg = con.execute("SELECT workspace, key, value FROM workspace_config").fetchall()
    assert cfg == [("default", "model", "anthropic:m")]
    con.close()
    assert not legacy.exists()
    assert (legacy.parent / "productagents.db.imported").exists()
    assert home.env_file.read_text() == "ANTHROPIC_API_KEY=k\n"
    workspaces = await WorkspaceService(home=home, engine=engine).list()
    assert [w["name"] for w in workspaces] == ["default"]


async def test_bootstrap_fresh_home_creates_schema_and_default(tmp_path):
    home = SharedHome(root=tmp_path)
    engine = make_engine(home.db_url)
    await bootstrap_home(home, engine=engine)
    workspaces = await WorkspaceService(home=home, engine=engine).list()
    assert [w["name"] for w in workspaces] == ["default"]


async def test_bootstrap_is_idempotent(tmp_path):
    home = SharedHome(root=tmp_path)
    legacy = home.legacy_workspaces_dir / "default" / "productagents.db"
    _make_legacy_db(legacy)
    engine = make_engine(home.db_url)
    await bootstrap_home(home, engine=engine)
    await bootstrap_home(home, engine=engine)  # second run: no-op, no crash
    con = sqlite3.connect(home.db_path)
    assert con.execute("SELECT COUNT(*) FROM memory_decision").fetchone() == (1,)
    con.close()
