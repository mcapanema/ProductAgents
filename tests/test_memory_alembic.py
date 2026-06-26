import subprocess
from pathlib import Path

from sqlalchemy import create_engine, inspect

_PA_MEMORY = Path(__file__).resolve().parents[1] / "packages" / "pa-memory"


def test_alembic_upgrade_creates_memory_tables(tmp_path):
    db = tmp_path / "mem.db"
    env = {"PRODUCTAGENTS_DB_URL": f"sqlite+aiosqlite:///{db}"}
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=_PA_MEMORY,
        env={**__import__("os").environ, **env},
        check=True,
    )
    sync = create_engine(f"sqlite:///{db}")
    with sync.connect() as conn:
        names = set(inspect(conn).get_table_names())
    assert {"memory_decision", "memory_outcome", "alembic_version_memory"} <= names
