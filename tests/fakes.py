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


class FakeChatModel:
    """Stands in for a LangChain chat model in tests.

    `results` maps a Pydantic schema class to the instance that
    `with_structured_output(schema).ainvoke(...)` should return. If the mapped
    value is an Exception instance, `ainvoke` raises it instead.
    """

    def __init__(self, results: dict):
        self._results = results

    def with_structured_output(self, schema, **_kwargs):
        if schema not in self._results:
            raise KeyError(f"FakeChatModel has no result for schema {schema!r}")
        return _FakeStructured(self._results[schema])
