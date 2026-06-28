import importlib.util
from pathlib import Path

_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "packages/pa-memory/alembic/versions/0002_event_store.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("mig_0002", _MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_chains_onto_memory_tables():
    mig = _load()
    assert mig.revision == "0002_event_store"
    assert mig.down_revision == "0001_memory_tables"
    assert callable(mig.upgrade)
    assert callable(mig.downgrade)
