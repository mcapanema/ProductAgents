"""Test doubles for offline agent/graph testing."""

from productagents.setup import ConfigStatus


def ready_status() -> ConfigStatus:
    """A ConfigStatus that reports the app is fully configured."""
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=True,
    )


class _FakeStructured:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, _input):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeSequenced:
    """Returns items from a list in order; repeats the last item once exhausted."""

    def __init__(self, sequence):
        self._sequence = list(sequence)
        self._index = 0

    async def ainvoke(self, _input):
        item = self._sequence[min(self._index, len(self._sequence) - 1)]
        self._index += 1
        if isinstance(item, Exception):
            raise item
        return item


class FakeChatModel:
    """Stands in for a LangChain chat model in tests.

    `results` maps a Pydantic schema class to the instance that
    `with_structured_output(schema).ainvoke(...)` should return. If the mapped
    value is an Exception instance, `ainvoke` raises it instead.

    To vary the response across multiple calls to the same schema, map the schema
    to a *list* of values. The first call returns `results[0]`, the second returns
    `results[1]`, etc. Once exhausted, the last value is repeated.

    Example (judge fails once, then passes)::

        model = FakeChatModel({
            JudgeFinding: [
                JudgeFinding(evidence_grounding_score=0.3, ...),  # fail
                JudgeFinding(evidence_grounding_score=0.9, ...),  # pass
            ],
        })
    """

    def __init__(self, results: dict):
        self._results = results
        # Pre-build _FakeSequenced instances so the call index persists across
        # multiple with_structured_output() calls for the same schema.
        self._structured: dict = {
            schema: _FakeSequenced(value)
            if isinstance(value, list)
            else _FakeStructured(value)
            for schema, value in results.items()
        }

    def with_structured_output(self, schema, **_kwargs):
        if schema not in self._structured:
            raise KeyError(f"FakeChatModel has no result for schema {schema!r}")
        return self._structured[schema]
