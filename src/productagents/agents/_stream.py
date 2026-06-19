"""Shared helper for emitting progress events from graph nodes."""

from langgraph.config import get_stream_writer


def get_writer():
    """Return the active stream writer, or a no-op when not inside a graph run.

    LangGraph raises RuntimeError if get_stream_writer() is called outside an
    active graph execution (e.g. in unit tests that call a node directly).
    """
    try:
        return get_stream_writer()
    except RuntimeError:
        return lambda _: None
