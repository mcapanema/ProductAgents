"""Test doubles for the memory subsystem (offline, deterministic)."""


class FakeEmbedder:
    """Maps exact initiative text → a chosen vector (the embedding analogue of
    FakeChatModel). Lets a test prove the semantic path surfaces a decision that
    shares no lexical tokens with the query."""

    def __init__(self, mapping: dict[str, list[float]], default: list[float]) -> None:
        self._mapping = mapping
        self._default = default

    def embed(self, text: str) -> list[float]:
        return self._mapping.get(text, self._default)
