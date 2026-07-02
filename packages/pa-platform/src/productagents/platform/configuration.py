"""Provider/config preflight + .env provisioning — platform-layer config service.

`check_config()` is a *static* readiness check: it determines the active model,
the provider that model implies, and whether the matching API-key environment
variable is present. It never makes a network call. `write_env()` persists the
values the setup wizard collects to a `.env` file (and the live process env) so
the next run is configured.

`ConfigurationService` wraps these helpers as an Application-Layer service that
targets the active workspace's `.env` on writes.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import find_dotenv, set_key

from productagents.agents.debate import get_debate_rounds
from productagents.agents.judge import get_judge_max_retries, get_judge_threshold
from productagents.core.config import env_int
from productagents.core.logging_config import DEFAULT_LEVEL
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
    """Current tunable values (env-or-default), for the Settings UI.

    Values come from the same getters the agents use, so the defaults shown in
    the GUI can never drift from the ones the pipeline applies. Secrets are
    reported as presence booleans only.
    """
    return {
        "debate_rounds": get_debate_rounds(),
        "judge_threshold": get_judge_threshold(),
        "judge_max_retries": get_judge_max_retries(),
        "max_retries": env_int(
            "PRODUCTAGENTS_MAX_RETRIES", DEFAULT_MAX_RETRIES, minimum=0
        ),
        "log_level": os.environ.get("PRODUCTAGENTS_LOG_LEVEL", DEFAULT_LEVEL).upper(),
        "github_repo": os.environ.get("PRODUCTAGENTS_GITHUB_REPO", ""),
        "github_token_present": bool(
            os.environ.get("PRODUCTAGENTS_GITHUB_TOKEN", "").strip()
        ),
    }


# Whitelist of GUI-writable settings → env var. Anything not listed here is
# silently dropped so the IPC surface can never write arbitrary env vars.
_SETTING_ENV: dict[str, str] = {
    "debate_rounds": "PRODUCTAGENTS_DEBATE_ROUNDS",
    "judge_threshold": "PRODUCTAGENTS_JUDGE_THRESHOLD",
    "judge_max_retries": "PRODUCTAGENTS_JUDGE_MAX_RETRIES",
    "max_retries": "PRODUCTAGENTS_MAX_RETRIES",
    "log_level": "PRODUCTAGENTS_LOG_LEVEL",
    "github_repo": "PRODUCTAGENTS_GITHUB_REPO",
    "github_token": "PRODUCTAGENTS_GITHUB_TOKEN",
}
_SECRET_SETTINGS = frozenset({"github_token"})


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

    Reading is the static, no-network ``check_config`` over ``os.environ``.
    Writing targets the active workspace's ``.env`` (first GUI write creates it),
    derives the provider from the model prefix when not given, and never writes a
    blank API key over an existing one.
    """

    def __init__(
        self,
        *,
        workspaces: WorkspaceService | None = None,
        active_name: str | None = None,
    ) -> None:
        self._workspaces = workspaces if workspaces is not None else WorkspaceService()
        self._active_name = active_name

    def status(self) -> ConfigStatus:
        return check_config()

    def providers(self) -> dict[str, ProviderInfo]:
        return PROVIDERS

    def settings(self) -> dict[str, object]:
        return current_settings()

    def set(
        self,
        model: str,
        *,
        provider: str | None = None,
        api_key: str | None = None,
        settings: Mapping[str, object] | None = None,
    ) -> ConfigStatus:
        values: dict[str, str] = {"PRODUCTAGENTS_MODEL": model}
        if provider:
            values["PRODUCTAGENTS_MODEL_PROVIDER"] = provider
        if api_key:  # never write a blank key over an existing one
            key_var = api_key_var_for(provider or provider_for(model))
            if key_var:
                values[key_var] = api_key
        for key, value in (settings or {}).items():
            var = _SETTING_ENV.get(key)
            if var is None or value is None:
                continue  # unknown key, or a null a raw IPC client sent
            text = str(value).strip()
            if key in _SECRET_SETTINGS and not text:
                continue  # never blank a stored secret
            values[var] = text
        write_env(values, dotenv_path=self._env_path())
        return self.status()

    def _env_path(self) -> str:
        return str(self._workspaces.resolve(self._active_name).env_file)
