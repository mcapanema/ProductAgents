"""Span-like structured logging — no OpenTelemetry dependency.

ProductAgents is a single-operator app with no tracing collector running, so a
full OTel SDK would be all ceremony and nothing to export to. ``span()`` is the
lazy equivalent: it times a block and logs one structured line
(``name duration_ms=… status=… <context>``) through the file logger. The yielded
``attrs`` dict lets the caller attach context (``written=14``, ``reports=5``)
that lands on the same line.

It lives in ``pa-core`` so every layer can use it — the connectors trace
``connector.sync``/``connector.health``; the agent graph traces ``decision.run``
and ``decision.<node>``.

ponytail: this is a logging shim, not real tracing. If a collector ever exists,
swap the body for ``tracer.start_as_current_span`` — the call sites don't change.
"""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger("productagents.observability")


@contextmanager
def span(name: str, **fields: object) -> Iterator[dict[str, object]]:
    """Time the block; log ``name duration_ms=… status=… <context>`` on exit."""
    start = time.monotonic()
    attrs: dict[str, object] = dict(fields)
    try:
        yield attrs
    except BaseException:
        attrs["status"] = "error"
        raise
    finally:
        attrs.setdefault("status", "ok")
        duration_ms = round((time.monotonic() - start) * 1000)
        rendered = " ".join(f"{key}={value}" for key, value in attrs.items())
        logger.info("%s duration_ms=%d %s", name, duration_ms, rendered)
