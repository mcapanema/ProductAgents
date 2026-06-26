"""Text → vector embedding for semantic recall.

``Embedder`` is the swap seam. ``HashingEmbedder`` is a deterministic,
dependency-free default: a hashed bag-of-words, good enough to exercise the
hybrid-retrieval plumbing offline and in CI.

ponytail: HashingEmbedder is a placeholder with no true semantics (it only
'matches' on shared tokens). The Phase-7 upgrade is to drop in a real model
(local sentence-transformers or a hosted embeddings API) behind this same
``Embedder`` protocol — no caller changes.
"""

import hashlib
import math
from typing import Protocol

from productagents.memory.retrieval import _tokens


class Embedder(Protocol):
    """Maps text to a fixed-length vector."""

    def embed(self, text: str) -> list[float]: ...


def _bucket(token: str, dim: int) -> int:
    # hashlib (not built-in hash()) so the vector is stable across processes.
    return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dim


class HashingEmbedder:
    """Deterministic hashed bag-of-words, L2-normalized."""

    def __init__(self, dim: int = 256) -> None:
        self._dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for token in _tokens(text):
            vec[_bucket(token, self._dim)] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec
        return [x / norm for x in vec]
