"""`alembic upgrade head` builds the sync_state schema from the migration."""

from pathlib import Path

import productagents.knowledge as knowledge_pkg

_PKG_ROOT = Path(knowledge_pkg.__file__).resolve().parents[3]  # packages/pa-knowledge
_ALEMBIC_INI = _PKG_ROOT / "alembic.ini"
_SCRIPT_LOCATION = _PKG_ROOT / "alembic"


def test_upgrade_head_creates_sync_state(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    db = tmp_path / "migrated.db"
    monkeypatch.setenv("PRODUCTAGENTS_DB_URL", f"sqlite+aiosqlite:///{db}")

    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_SCRIPT_LOCATION))
    command.upgrade(cfg, "head")

    insp = inspect(create_engine(f"sqlite:///{db}"))
    assert "sync_state" in insp.get_table_names()
    columns = {c["name"] for c in insp.get_columns("sync_state")}
    assert {"workspace", "connector_key", "cursor_value", "updated_at"} == columns
