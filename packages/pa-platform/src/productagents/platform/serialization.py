"""Serialize platform Events to/from the primitive rows the Event Store persists.

The Event Store (pa-memory) sits below the platform and knows nothing about the
Event vocabulary; this module is the bridge. pydantic's ``TypeAdapter`` handles
the nested canonical models (``AnalystReport``, ``Recommendation``, …), datetimes,
lists, and optionals for free, so every event type round-trips with no per-type
code — a new event needs no change here.
"""

from functools import cache

from pydantic import TypeAdapter

from productagents.platform import events as ev


@cache
def _adapter(cls: type) -> TypeAdapter:
    return TypeAdapter(cls)


@cache
def _event_types() -> dict[str, type]:
    # Every event is a direct subclass of Event (see events.py).
    return {cls.__name__: cls for cls in ev.Event.__subclasses__()}


def serialize_event(event: ev.Event) -> tuple[str, dict]:
    """Return ``(event_type_name, json-safe payload dict)`` for one event."""
    cls = type(event)
    return cls.__name__, _adapter(cls).dump_python(event, mode="json")


def deserialize_event(event_type: str, payload: dict) -> ev.Event:
    """Reconstruct the original Event subclass from a stored row."""
    return _adapter(_event_types()[event_type]).validate_python(payload)
