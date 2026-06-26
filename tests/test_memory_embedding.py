import math

from productagents.memory.embedding import HashingEmbedder


def test_embedding_is_deterministic_and_unit_length():
    e = HashingEmbedder(dim=64)
    v1 = e.embed("Add enterprise SSO login")
    v2 = e.embed("Add enterprise SSO login")
    assert v1 == v2
    assert len(v1) == 64
    assert math.isclose(math.sqrt(sum(x * x for x in v1)), 1.0, rel_tol=1e-9)


def test_shared_tokens_produce_overlapping_vectors():
    e = HashingEmbedder(dim=128)
    a = e.embed("enterprise SSO authentication")
    b = e.embed("enterprise SSO rollout")
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    assert dot > 0.0  # they share "enterprise" + "sso"


def test_empty_text_yields_zero_vector():
    assert HashingEmbedder(dim=8).embed("the a an") == [0.0] * 8
