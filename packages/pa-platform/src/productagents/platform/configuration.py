"""Provider/config preflight + .env provisioning — platform-layer config service.

`check_config()` is a *static* readiness check: it determines the active model,
the provider that model implies, and whether the matching API-key environment
variable is present. It never makes a network call. `write_env()` persists the
values the setup wizard collects to a `.env` file (and the live process env) so
the next run is configured.

`ConfigurationService` wraps these helpers as an Application-Layer service.
Workspace configuration lives in the workspace database and is materialized
into the process environment once at startup (`load()`), giving the
precedence CLI args > exported env > workspace DB > built-in defaults from a
single mechanism. Secrets stay in the workspace `.env`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values, find_dotenv, set_key, unset_key

from productagents.agents.debate import get_debate_rounds
from productagents.agents.judge import get_judge_max_retries, get_judge_threshold
from productagents.core.config import env_int
from productagents.platform.llm import DEFAULT_MAX_RETRIES, DEFAULT_MODEL
from productagents.platform.workspace import WorkspaceService


@dataclass(frozen=True)
class ProviderInfo:
    """Metadata for a supported model provider."""

    label: str  # human-readable name shown in the setup UI
    key_var: str  # environment variable for the API key
    default_model: str  # suggested full model string for this provider


# Ordered by popularity; CN variants grouped at the end.
PROVIDERS: dict[str, ProviderInfo] = {
    "anthropic": ProviderInfo(
        "Anthropic", "ANTHROPIC_API_KEY", "anthropic:claude-sonnet-4-6"
    ),
    "openai": ProviderInfo("OpenAI", "OPENAI_API_KEY", "openai:gpt-4o"),
    "google_genai": ProviderInfo(
        "Google", "GOOGLE_API_KEY", "google_genai:gemini-2.0-flash"
    ),
    "xai": ProviderInfo("xAI (Grok)", "XAI_API_KEY", "xai:grok-2"),
    "deepseek": ProviderInfo("DeepSeek", "DEEPSEEK_API_KEY", "deepseek:deepseek-chat"),
    "openrouter": ProviderInfo(
        "OpenRouter",
        "OPENROUTER_API_KEY",
        "openrouter:deepseek/deepseek-chat-v3-0324:free",
    ),
    "groq": ProviderInfo("Groq", "GROQ_API_KEY", "groq:llama-3.3-70b-versatile"),
    "mistralai": ProviderInfo(
        "Mistral", "MISTRAL_API_KEY", "mistralai:mistral-large-latest"
    ),
    "moonshot": ProviderInfo("Moonshot", "MOONSHOT_API_KEY", "moonshot:moonshot-v1-8k"),
    "nvidia": ProviderInfo(
        "NVIDIA NIM", "NVIDIA_API_KEY", "nvidia:meta/llama-3.1-70b-instruct"
    ),
    "dashscope": ProviderInfo(
        "DashScope (Alibaba)", "DASHSCOPE_API_KEY", "dashscope:qwen-plus"
    ),
    "dashscope_cn": ProviderInfo(
        "DashScope (CN)", "DASHSCOPE_CN_API_KEY", "dashscope_cn:qwen-plus"
    ),
    "zhipu": ProviderInfo("ZhipuAI", "ZHIPU_API_KEY", "zhipu:glm-4"),
    "zhipu_cn": ProviderInfo("ZhipuAI (CN)", "ZHIPU_CN_API_KEY", "zhipu_cn:glm-4"),
    "minimax": ProviderInfo("MiniMax", "MINIMAX_API_KEY", "minimax:abab6.5s-chat"),
    "minimax_cn": ProviderInfo(
        "MiniMax (CN)", "MINIMAX_CN_API_KEY", "minimax_cn:abab6.5s-chat"
    ),
}

# Derived from PROVIDERS; still used by check_config / api_key_var_for.
PROVIDER_API_KEYS: dict[str, str] = {
    pid: info.key_var for pid, info in PROVIDERS.items()
}


def provider_for(model: str, explicit_provider: str | None = None) -> str:
    """Resolve the provider name for a model id.

    An explicit `PRODUCTAGENTS_MODEL_PROVIDER` wins. Otherwise the provider is
    the prefix before the first ':' in a `provider:model` id (e.g.
    "anthropic:claude-..." -> "anthropic"). Returns "" when it can't be
    determined (a bare model id with no provider prefix).
    """
    if explicit_provider:
        return explicit_provider.strip()
    if ":" in model:
        return model.split(":", 1)[0].strip()
    return ""


def api_key_var_for(provider: str) -> str:
    """Return the API-key env var name for a provider.

    Known providers come from PROVIDER_API_KEYS; unknown but non-empty
    providers get a derived "<PROVIDER>_API_KEY" name. An empty provider
    yields "".
    """
    if not provider:
        return ""
    return PROVIDER_API_KEYS.get(provider, f"{provider.upper()}_API_KEY")


@dataclass(frozen=True)
class ConfigStatus:
    """The result of a static readiness check."""

    model: str
    provider: str
    key_var: str
    key_present: bool
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def check_config(env: Mapping[str, str] | None = None) -> ConfigStatus:
    """Statically check whether a model + matching API key are configured.

    Reads from `env` (defaults to `os.environ`). Never makes a network call.
    """
    if env is None:
        env = os.environ
    model = env.get("PRODUCTAGENTS_MODEL", DEFAULT_MODEL)
    provider = provider_for(model, env.get("PRODUCTAGENTS_MODEL_PROVIDER"))
    key_var = api_key_var_for(provider)
    key_present = bool(env.get(key_var, "").strip()) if key_var else False

    problems: list[str] = []
    if not provider:
        problems.append(
            f"Could not determine a provider from model '{model}'. "
            "Use a 'provider:model' id or set PRODUCTAGENTS_MODEL_PROVIDER."
        )
    elif not key_present:
        problems.append(f"Missing API key: set {key_var} for provider '{provider}'.")

    return ConfigStatus(
        model=model,
        provider=provider,
        key_var=key_var,
        key_present=key_present,
        problems=problems,
    )


def current_settings() -> dict[str, object]:
    """Current tunable values (resolved env-or-default), for the Settings UI.

    Values come from the same getters the agents use, so the defaults shown in
    the GUI can never drift from the ones the pipeline applies. ``load()`` has
    already materialized workspace-DB values into the environment, so this
    reflects the full precedence chain.
    """
    return {
        "debate_rounds": get_debate_rounds(),
        "judge_threshold": get_judge_threshold(),
        "judge_max_retries": get_judge_max_retries(),
        "max_retries": env_int(
            "PRODUCTAGENTS_MAX_RETRIES", DEFAULT_MAX_RETRIES, minimum=0
        ),
    }


# Workspace configuration: friendly key -> env var. This is the ONLY set of
# keys the DB path handles; anything else from the wire is silently dropped so
# IPC can never write arbitrary env vars. Secrets are deliberately absent —
# they live in the workspace .env, never the database.
_WORKSPACE_ENV: dict[str, str] = {
    "model": "PRODUCTAGENTS_MODEL",
    "model_provider": "PRODUCTAGENTS_MODEL_PROVIDER",
    "debate_rounds": "PRODUCTAGENTS_DEBATE_ROUNDS",
    "judge_threshold": "PRODUCTAGENTS_JUDGE_THRESHOLD",
    "judge_max_retries": "PRODUCTAGENTS_JUDGE_MAX_RETRIES",
    "max_retries": "PRODUCTAGENTS_MAX_RETRIES",
}
# The subset settable through set(settings=...); model/model_provider are
# explicit arguments there.
_TUNABLE_KEYS = frozenset(
    {"debate_rounds", "judge_threshold", "judge_max_retries", "max_retries"}
)


def write_env(
    values: Mapping[str, str],
    *,
    dotenv_path: str | os.PathLike[str] | None = None,
) -> str:
    """Persist `values` to a .env file and the live process environment.

    With `dotenv_path=None`, an existing .env is discovered (walking up from the
    cwd); if none exists, `.env` in the cwd is created. Each key is written with
    python-dotenv's `set_key` (preserving other lines) and also set in
    `os.environ` so the current run picks it up immediately. Returns the path
    written.
    """
    if dotenv_path is not None:
        path = str(dotenv_path)
    else:
        path = find_dotenv(usecwd=True) or os.path.join(os.getcwd(), ".env")

    if not os.path.exists(path):
        # set_key needs an existing file on some python-dotenv versions.
        with open(path, "a", encoding="utf-8"):
            pass

    for key, value in values.items():
        set_key(path, key, value)
        os.environ[key] = value
    return path


class ConfigurationService:
    """Application-Layer owner of read/write config for the active workspace.

    The single entry point for configuration. Precedence for workspace config
    is CLI args > exported env > workspace DB > built-in defaults, implemented
    here and nowhere else: ``apply_overrides`` writes the env (top tier),
    ``load()`` seeds the env from the DB via ``setdefault`` (never overrides),
    and the built-in defaults stay in the agents' getters (bottom tier).
    Reading is the static, no-network ``check_config`` over ``os.environ``.
    Secrets (API keys) still write to the workspace ``.env`` and never enter
    the database.
    """

    def __init__(
        self,
        *,
        workspaces: WorkspaceService | None = None,
        active_name: str = "default",
        engine=None,
    ) -> None:
        self._workspaces = workspaces if workspaces is not None else WorkspaceService()
        self._active_name = active_name
        self._engine = engine  # test seam; None -> process-wide engine
        self._seeded: set[str] = set()  # keys whose env value came from the DB
        self._overrides: set[str] = set()  # keys set via CLI --set

    # -- plumbing ---------------------------------------------------------

    def _sessionmaker(self):
        from productagents.knowledge.repositories.sqlmodel.engine import (
            make_sessionmaker,
        )
        from productagents.platform.context import get_engine

        return make_sessionmaker(self._engine or get_engine())

    async def _ensure_schema(self) -> None:
        from productagents.memory.store import create_all
        from productagents.platform.context import get_engine

        await create_all(self._engine or get_engine())

    def _env_path(self) -> str:
        return str(self._workspaces.home().env_file)

    # -- precedence -------------------------------------------------------

    def apply_overrides(self, overrides: Mapping[str, str]) -> None:
        """CLI-argument tier: write each override into the environment.

        Runs before ``load()``; because ``load()`` only ``setdefault``s, an
        override outranks both shell exports and the workspace DB.
        """
        for key, value in overrides.items():
            var = _WORKSPACE_ENV.get(key)
            if var is None:
                valid = ", ".join(sorted(_WORKSPACE_ENV))
                raise ValueError(f"unknown setting: {key!r} (valid: {valid})")
            os.environ[var] = str(value)
            self._overrides.add(key)

    async def load(self) -> None:
        """Materialize workspace-DB config into the environment (startup, once).

        Bootstraps the schema (idempotent; Alembic owns the real migration
        history), migrates legacy workspace keys out of the workspace ``.env``
        into the DB, then seeds ``os.environ`` from the DB with ``setdefault``
        so anything already present (export or override) keeps winning.
        """
        await self._ensure_schema()
        from productagents.memory.workspace_state import WorkspaceConfigStore

        async with self._sessionmaker()() as session:
            store = WorkspaceConfigStore(session, self._active_name)
            await self._migrate_env_file(store)
            for key, value in (await store.all()).items():
                var = _WORKSPACE_ENV.get(key)
                if var is None:
                    continue  # a key from another version; ignore, don't crash
                if var not in os.environ:
                    os.environ[var] = value
                    self._seeded.add(key)

    async def switch(self, name: str) -> None:
        """Re-scope to ``name`` and re-materialize the db/default tiers.

        Only keys this service seeded (or that nothing supplies) are touched:
        a shell export (origin ``env``) and a CLI ``--set`` (origin
        ``override``) keep winning across switches, exactly like at startup.
        """
        self._active_name = name
        await self._ensure_schema()
        from productagents.memory.workspace_state import WorkspaceConfigStore

        async with self._sessionmaker()() as session:
            stored = await WorkspaceConfigStore(session, name).all()
        for key, var in _WORKSPACE_ENV.items():
            if key in self._overrides:
                continue
            # ponytail: _seeded is bookkeeping-truth — a later manual os.environ
            # mutation of a seeded key is treated as service-owned and overwritten
            # on switch; re-detect live values if that ever bites.
            owned = key in self._seeded or var not in os.environ
            if not owned:
                continue  # shell export tier — never touch
            value = stored.get(key)
            if value is None:
                os.environ.pop(var, None)
                self._seeded.discard(key)
            else:
                os.environ[var] = value
                self._seeded.add(key)

    async def _migrate_env_file(self, store) -> None:
        """One-time move of workspace keys out of the workspace ``.env``.

        Without removal, stale ``.env`` lines would out-rank the DB forever and
        GUI saves would silently not apply. Secrets and runtime keys are never
        touched. Idempotent: migrated keys are gone from the file, and an
        existing DB row blocks re-import (the stale line is still removed).
        """
        env_path = Path(self._env_path())
        if not env_path.exists():
            return
        stored = await store.all()
        file_values = dotenv_values(env_path)
        for key, var in _WORKSPACE_ENV.items():
            raw = file_values.get(var)
            if raw is None:
                continue
            if key not in stored:
                await store.set(key, raw)
            unset_key(str(env_path), var)
            if os.environ.get(var) == raw:
                # The process value came from the file we just migrated (it was
                # loaded by activate()); drop it so the DB tier takes over.
                del os.environ[var]

    # -- reads --------------------------------------------------------------

    def status(self) -> ConfigStatus:
        return check_config()

    def providers(self) -> dict[str, ProviderInfo]:
        return PROVIDERS

    def settings(self) -> dict[str, object]:
        return current_settings()

    def settings_origins(self) -> dict[str, str]:
        """Which precedence tier supplies each workspace key right now.

        ``override`` (CLI --set) > ``env`` (shell export) > ``db`` > ``default``.
        Lets the GUI label a field "overridden by environment" instead of a
        save that mysteriously doesn't apply.
        """
        origins: dict[str, str] = {}
        for key, var in _WORKSPACE_ENV.items():
            if key in self._overrides:
                origins[key] = "override"
            elif key in self._seeded:
                origins[key] = "db"
            elif var in os.environ:
                origins[key] = "env"
            else:
                origins[key] = "default"
        return origins

    # -- writes -------------------------------------------------------------

    async def set(
        self,
        model: str,
        *,
        provider: str | None = None,
        api_key: str | None = None,
        settings: Mapping[str, object] | None = None,
    ) -> ConfigStatus:
        db_values: dict[str, str] = {"model": model}
        if provider:
            db_values["model_provider"] = provider
        for key, value in (settings or {}).items():
            if key in _TUNABLE_KEYS and value is not None:
                db_values[key] = str(value).strip()

        await self._ensure_schema()
        from productagents.memory.workspace_state import WorkspaceConfigStore

        async with self._sessionmaker()() as session:
            store = WorkspaceConfigStore(session, self._active_name)
            for key, value in db_values.items():
                await store.set(key, value)
                var = _WORKSPACE_ENV[key]
                refreshable = key in self._seeded or var not in os.environ
                if key not in self._overrides and refreshable:
                    os.environ[var] = value  # next run picks it up, no restart
                    self._seeded.add(key)

        if api_key:  # never write a blank key over an existing one
            key_var = api_key_var_for(provider or provider_for(model))
            if key_var:
                write_env({key_var: api_key}, dotenv_path=self._env_path())
        return self.status()
