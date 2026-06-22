"""Shared structured-output call wrapper.

Every node issues exactly one `model.with_structured_output(Schema).ainvoke(prompt)`
call. Routing them all through `invoke_structured` gives one chokepoint to:
- log each call (and full tracebacks on failure) for debugging, and
- convert a `None` result — which a model that does not support tool/function
  calling returns instead of structured data — into an actionable
  `StructuredOutputError` rather than a cryptic `AttributeError` downstream
  (e.g. `'NoneType' object has no attribute 'findings'`).

Callers keep their own `try/except` graceful-degradation path; this only
standardizes the call, its logging, and the empty-result case.
"""

import logging

logger = logging.getLogger(__name__)


class StructuredOutputError(RuntimeError):
    """Raised when a structured-output call returns no parsed object.

    A `None` result almost always means the configured model does not support
    tool/function calling, which `with_structured_output` requires.
    """


async def invoke_structured(model, schema, prompt, *, node):
    """Run one structured-output call, logging it and rejecting empty results.

    Returns the parsed `schema` instance. Raises `StructuredOutputError` if the
    model returns `None` (no tool call), or re-raises any provider exception
    after logging its traceback.
    """
    logger.debug("node=%s invoking model for %s", node, schema.__name__)
    try:
        result = await model.with_structured_output(schema).ainvoke(prompt)
    except Exception:
        logger.exception("node=%s structured call failed for %s", node, schema.__name__)
        raise
    if result is None:
        logger.error(
            "node=%s structured call returned None for %s — the configured model "
            "likely does not support tool/function calling",
            node,
            schema.__name__,
        )
        raise StructuredOutputError(
            f"model returned no structured output for {schema.__name__}; the "
            "configured model likely does not support tool/function calling, "
            "which structured output requires"
        )
    logger.debug("node=%s structured call ok for %s", node, schema.__name__)
    return result
