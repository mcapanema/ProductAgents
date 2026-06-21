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

from productagents.llm import DEFAULT_MODEL

# provider -> the environment variable holding its API key. Extensible: an
# unknown but non-empty provider falls back to a derived "<PROVIDER>_API_KEY"
# name in api_key_var_for, so new providers work without code changes.
PROVIDER_API_KEYS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google_genai": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistralai": "MISTRAL_API_KEY",
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
