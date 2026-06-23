from productagents.core.ids import InitiativeId, new_id


def test_new_id_is_unique_hex():
    a, b = new_id(), new_id()
    assert a != b
    assert len(a) == 32
    assert int(a, 16) >= 0  # valid hex


def test_newtype_is_str_at_runtime():
    iid = InitiativeId(new_id())
    assert isinstance(iid, str)
