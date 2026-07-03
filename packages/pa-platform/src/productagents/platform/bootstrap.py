"""One-time home bootstrap: adopt the legacy default-workspace DB, ensure schema.

Follows the repo's one-time-import precedent (connectors.yaml -> .imported):
the legacy file is consumed once and renamed so adoption can never re-run.
Runtime schema creation is ``create_all`` over both metadatas; the Alembic
histories remain the dev/Postgres source of truth.

ponytail: create_all suffices because the shared DB is NEW in this release —
the first post-release schema change must add programmatic Alembic upgrade
here (both packages' histories) before touching the tables.
"""

from __future__ import annotations

import logging
import os
import sqlite3

from productagents.platform.workspace import DEFAULT_WORKSPACE, SharedHome

logger = logging.getLogger(__name__)

# Legacy tables to adopt -> whether they gain the workspace column.
_TABLES = {
    "memory_decision": True,
    "memory_outcome": True,
    "runtime_session": True,
    "runtime_event": False,
    "workspace_config": True,
    "connector_config": True,
    "preference": False,
    "canonical_record": True,
    "sync_state": True,
}


def _legacy_db(home: SharedHome):
    return home.legacy_workspaces_dir / DEFAULT_WORKSPACE / "productagents.db"


def _warn_other_legacy_workspaces(home: SharedHome) -> None:
    """Flag legacy workspace dirs besides ``default/`` — only default is adopted."""
    legacy_dir = home.legacy_workspaces_dir
    if not legacy_dir.is_dir():
        return
    others = [
        p.name
        for p in legacy_dir.iterdir()
        if p.is_dir() and p.name != DEFAULT_WORKSPACE
    ]
    if others:
        logger.warning(
            "legacy workspace dir(s) %s not auto-imported; see docs", sorted(others)
        )


def _adopt_env(home: SharedHome) -> None:
    legacy_env = home.legacy_workspaces_dir / DEFAULT_WORKSPACE / ".env"
    if not home.env_file.exists() and legacy_env.exists():
        try:
            os.replace(legacy_env, home.env_file)
        except OSError:
            # degrade, never crash: env adoption failing must not block startup
            logger.error("legacy .env adoption failed; starting fresh", exc_info=True)


def _copy_rows(home: SharedHome) -> None:
    """ATTACH the legacy DB and copy its rows, stamped 'default', then retire it."""
    legacy = _legacy_db(home)
    con = sqlite3.connect(home.db_path)
    try:
        con.execute("ATTACH DATABASE ? AS legacy", (str(legacy),))
        for table, scoped in _TABLES.items():
            exists = con.execute(
                "SELECT name FROM legacy.sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if exists is None:
                continue
            # ponytail: assumes the only legacy→current delta is the workspace
            # column (true for the one legacy generation that exists); a legacy
            # DB missing other NOT-NULL columns degrades via the outer except —
            # logged, never imported.
            cols = [
                r[1]
                for r in con.execute(f"PRAGMA legacy.table_info({table})").fetchall()
            ]
            col_list = ", ".join('"' + c.replace('"', '""') + '"' for c in cols)
            # B608: not injectable — `table` comes from the hardcoded _TABLES
            # dict, `col_list` identifiers are double-quote-escaped above, and
            # DEFAULT_WORKSPACE is a module constant.
            if scoped:
                stmt = (
                    f"INSERT OR IGNORE INTO main.{table} ({col_list}, workspace) "  # nosec B608
                    f"SELECT {col_list}, '{DEFAULT_WORKSPACE}' FROM legacy.{table}"
                )
            else:
                stmt = (
                    f"INSERT OR IGNORE INTO main.{table} ({col_list}) "  # nosec B608
                    f"SELECT {col_list} FROM legacy.{table}"
                )
            con.execute(stmt)
        con.commit()
        con.execute("DETACH DATABASE legacy")
    finally:
        con.close()
    os.replace(legacy, str(legacy) + ".imported")


async def bootstrap_home(home: SharedHome, *, engine=None) -> None:
    """Idempotent startup bootstrap: adopt legacy data, ensure schema + default row."""
    from productagents.knowledge.repositories.sqlmodel.engine import (
        create_all as knowledge_create_all,
    )
    from productagents.knowledge.repositories.sqlmodel.engine import make_sessionmaker
    from productagents.memory.store import create_all as memory_create_all
    from productagents.memory.workspace_state import WorkspaceRegistry
    from productagents.platform.context import get_engine

    home.root.mkdir(parents=True, exist_ok=True)
    # Ordering trap: decide adoption BEFORE create_all runs, since create_all
    # is what brings home.db_path into existence.
    adopt = not home.db_path.exists() and _legacy_db(home).exists()
    _adopt_env(home)
    _warn_other_legacy_workspaces(home)

    engine = engine if engine is not None else get_engine()
    await knowledge_create_all(engine)
    await memory_create_all(engine)

    if adopt:
        try:
            # The legacy-DB copy and its .imported rename are one adoption step —
            # a rename failure (e.g. cross-device, permissions) must degrade the
            # same way a corrupt legacy DB does, so OSError joins sqlite3.Error.
            _copy_rows(home)
        except sqlite3.Error, OSError:
            # degrade, never crash: a bad legacy file must not block startup
            logger.error("legacy DB adoption failed; starting fresh", exc_info=True)

    maker = make_sessionmaker(engine)
    async with maker() as session:
        registry = WorkspaceRegistry(session)
        # Seed the fallback workspace only on an empty registry — a renamed
        # `default` must not ghost back as a fresh empty workspace next launch.
        if not await registry.list():
            await registry.ensure(DEFAULT_WORKSPACE)
