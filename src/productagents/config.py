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


def env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    """Read an int env var, falling back to `default` on absence/parse error.

    When `minimum` is given, values below it also fall back to `default`.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    return value


def env_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """Read a float env var, falling back to `default` on absence/parse error.

    When `minimum`/`maximum` are given, values outside the inclusive range also
    fall back to `default`.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    if maximum is not None and value > maximum:
        return default
    return value
