"""`alembic upgrade head` builds the canonical_record schema from the migration."""

from pathlib import Path

import productagents.knowledge as knowledge_pkg

_PKG_ROOT = Path(knowledge_pkg.__file__).resolve().parents[3]  # packages/pa-knowledge
_ALEMBIC_INI = _PKG_ROOT / "alembic.ini"
_SCRIPT_LOCATION = _PKG_ROOT / "alembic"


def test_upgrade_head_creates_canonical_record(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    db = tmp_path / "migrated.db"
    monkeypatch.setenv("PRODUCTAGENTS_DB_URL", f"sqlite+aiosqlite:///{db}")

    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_SCRIPT_LOCATION))
    command.upgrade(cfg, "head")

    insp = inspect(create_engine(f"sqlite:///{db}"))
    assert "canonical_record" in insp.get_table_names()
    columns = {c["name"] for c in insp.get_columns("canonical_record")}
    assert {
        "pk",
        "workspace",
        "model_type",
        "connector",
        "vendor_type",
        "vendor_id",
        "raw_fingerprint",
        "ingested_at",
        "updated_at",
        "payload",
    } == columns
    index_names = {ix["name"] for ix in insp.get_indexes("canonical_record")}
    assert "ix_canonical_record_model_type" in index_names
