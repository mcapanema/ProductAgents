"""Span-like structured logging for the connector layer — no OTel dependency.

The app is a single-operator TUI with no tracing collector running, so a full
OpenTelemetry SDK would be all ceremony and nothing to export to. ``span()`` is
the lazy equivalent: it times a block and logs one structured line
(``name duration_ms=… status=… <context>``) through the existing file logger.
The yielded ``attrs`` dict lets the caller attach context (``written=14``,
``category=auth``) that lands in the same line.

ponytail: this is a logging shim, not real tracing. If a collector ever exists,
swap the body for ``tracer.start_as_current_span`` — the call sites don't change.
"""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger("productagents.connectors")


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
