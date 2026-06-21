"""Startup configuration loading.

Loads environment variables from a `.env` file so users don't have to
`export` `PRODUCTAGENTS_*` settings and provider API keys by hand. Called
once at the `productagents` entry point, before any node reads `os.environ`.
"""

import os

from dotenv import load_dotenv


def load_env(dotenv_path: str | os.PathLike[str] | None = None) -> bool:
    """Load variables from a `.env` file into the process environment.

    With the default `dotenv_path=None`, the nearest `.env` is discovered by
    walking up from the current working directory. Existing environment
    variables are never overwritten (`override=False`), so a value exported in
    the shell always wins over the file. Returns `True` if a file was loaded.
    """
    return load_dotenv(dotenv_path=dotenv_path, override=False)
