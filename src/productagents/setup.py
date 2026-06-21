"""Provider/config preflight + .env provisioning for first-run setup.

`check_config()` is a *static* readiness check: it determines the active model,
the provider that model implies, and whether the matching API-key environment
variable is present. It never makes a network call. `write_env()` persists the
values the setup wizard collects to a `.env` file (and the live process env) so
the next run is configured.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import find_dotenv, set_key

from productagents.llm import DEFAULT_MODEL


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
        "OpenRouter", "OPENROUTER_API_KEY", "openrouter:openai/gpt-4o"
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
