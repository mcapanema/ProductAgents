"""Provider-agnostic chat-model factory.

Every agent obtains its model through `get_model()` so the provider can be
swapped via configuration without touching agent code.
"""

import logging
import os

from langchain.chat_models import init_chat_model

from productagents.config import env_int

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "anthropic:claude-sonnet-4-6"
# Free OpenRouter models throw transient upstream 429/5xx ("Provider returned
# error") under load; the underlying client honors Retry-After, so a bounded
# retry budget with backoff absorbs these without crashing a node.
DEFAULT_MAX_RETRIES = 6


def get_model():
    """Return a chat model selected by environment configuration.

    `PRODUCTAGENTS_MODEL` sets the model (default `DEFAULT_MODEL`). When given,
    `PRODUCTAGENTS_MODEL_PROVIDER` is passed through as `model_provider`.
    `PRODUCTAGENTS_MAX_RETRIES` (default 6) sets the client's automatic
    retry-with-backoff budget for transient provider errors.
    """
    model = os.environ.get("PRODUCTAGENTS_MODEL", DEFAULT_MODEL)
    provider = os.environ.get("PRODUCTAGENTS_MODEL_PROVIDER")
    max_retries = env_int("PRODUCTAGENTS_MAX_RETRIES", DEFAULT_MAX_RETRIES, minimum=0)
    if provider:
        logger.info("resolved model: %s (provider=%s)", model, provider)
        return init_chat_model(model, model_provider=provider, max_retries=max_retries)
    logger.info("resolved model: %s", model)
    return init_chat_model(model, max_retries=max_retries)
