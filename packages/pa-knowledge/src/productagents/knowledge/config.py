"""Storage configuration for the knowledge layer."""

import os

_DEFAULT_DB_URL = "sqlite+aiosqlite:///productagents.db"


def database_url() -> str:
    """The async SQLAlchemy URL for the canonical store.

    Defaults to a local SQLite file (the v1 "just works locally" ethos). Override
    with ``PRODUCTAGENTS_DB_URL`` (e.g. a ``postgresql+asyncpg://`` URL for scale).
    """
    return os.environ.get("PRODUCTAGENTS_DB_URL", _DEFAULT_DB_URL)
