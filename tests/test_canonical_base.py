from datetime import datetime

from productagents.core.models._base import CanonicalModel, fingerprint


def test_defaults_make_a_bare_subclass_constructible():
    class Thing(CanonicalModel):
        name: str

    t = Thing(name="x")
    assert isinstance(t.id, str)
    assert t.id
    assert t.source.connector == "manual"
    assert isinstance(t.ingested_at, datetime)
    assert isinstance(t.updated_at, datetime)
    assert t.raw_fingerprint is None
    assert t.extensions == {}


def test_round_trips_through_json():
    class Thing(CanonicalModel):
        name: str

    t = Thing(name="x", extensions={"vendor_color": "blue"})
    assert Thing.model_validate_json(t.model_dump_json()) == t


def test_two_instances_get_distinct_ids():
    class Thing(CanonicalModel):
        name: str

    assert Thing(name="a").id != Thing(name="b").id


def test_fingerprint_is_stable_and_order_independent():
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})
    assert fingerprint({"a": 1}) != fingerprint({"a": 2})
    assert len(fingerprint({"a": 1})) == 64  # sha256 hex
