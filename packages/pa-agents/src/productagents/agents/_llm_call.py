"""Shared structured-output call wrapper.

Every node issues exactly one `model.with_structured_output(Schema).ainvoke(prompt)`
call. Routing them all through `invoke_structured` gives one chokepoint to:
- log each call (and full tracebacks on failure) for debugging,
- convert a raw provider exception into a classified `ProviderError` carrying a
  friendly message (see `productagents.agents.llm_errors`), and
- convert a `None` result — which a model that does not support tool/function
  calling returns instead of structured data — into a clear
  `StructuredOutputError` rather than a cryptic `AttributeError` downstream.

When a failure is *fatal* (systemic for the whole run: bad key, exhausted rate
limit, no tool calling), the wrapper emits a `fatal` stream marker via the
active writer so the runner can stop the run instead of degrading node after
node. Callers keep their own `try/except` graceful-degradation path; this only
standardizes the call, its logging, the empty-result case, and the fatal signal.
"""

import logging

from productagents.agents._stream import get_writer
from productagents.agents.llm_errors import (
    ProviderError,
    StructuredOutputError,
    classify_provider_error,
)

logger = logging.getLogger(__name__)

# Re-exported so existing importers (`from ..._llm_call import StructuredOutputError`)
# keep working now that the type lives in `llm_errors`.
__all__ = ["ProviderError", "StructuredOutputError", "invoke_structured"]


def _emit_fatal(node: str, error: ProviderError) -> None:
    """Tell the runner this failure is systemic so it can stop the run early."""
    get_writer()(
        {
            "node": node,
            "error": str(error),
            "fatal": True,
            "category": error.category,
        }
    )


async def invoke_structured(model, schema, prompt, *, node):
    """Run one structured-output call, logging it and classifying failures.

    Returns the parsed `schema` instance. Raises `StructuredOutputError` if the
    model returns `None` (no tool call), or a classified `ProviderError` wrapping
    any provider exception. On a fatal category, emits a `fatal` stream marker
    before raising.
    """
    logger.debug("node=%s invoking model for %s", node, schema.__name__)
    try:
        result = await model.with_structured_output(schema).ainvoke(prompt)
    except Exception as exc:
        error = classify_provider_error(exc)
        logger.exception(
            "node=%s structured call failed for %s: %s", node, schema.__name__, error
        )
        if error.fatal:
            _emit_fatal(node, error)
        raise error from exc
    if result is None:
        error = StructuredOutputError(
            f"model returned no structured output for {schema.__name__}; the "
            "configured model likely does not support tool/function calling, "
            "which structured output requires"
        )
        logger.error(
            "node=%s structured call returned None for %s — the configured model "
            "likely does not support tool/function calling",
            node,
            schema.__name__,
        )
        _emit_fatal(node, error)
        raise error
    logger.debug("node=%s structured call ok for %s", node, schema.__name__)
    return result
