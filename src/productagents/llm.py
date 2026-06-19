"""Provider-agnostic chat-model factory.

Every agent obtains its model through `get_model()` so the provider can be
swapped via configuration without touching agent code.
"""

import os

from langchain.chat_models import init_chat_model

DEFAULT_MODEL = "anthropic:claude-sonnet-4-6"


def get_model():
    """Return a chat model selected by environment configuration.

    `PRODUCTAGENTS_MODEL` sets the model (default `DEFAULT_MODEL`). When given,
    `PRODUCTAGENTS_MODEL_PROVIDER` is passed through as `model_provider`.
    """
    model = os.environ.get("PRODUCTAGENTS_MODEL", DEFAULT_MODEL)
    provider = os.environ.get("PRODUCTAGENTS_MODEL_PROVIDER")
    if provider:
        return init_chat_model(model, model_provider=provider)
    return init_chat_model(model)
