"""Tests for the shared structured-output wrapper."""

import pytest
from productagents.agents._llm_call import StructuredOutputError, invoke_structured
from productagents.agents.llm_errors import ErrorCategory, ProviderError
from productagents.core.schemas import AnalystFindings

from tests.fakes import FakeChatModel


async def test_invoke_structured_returns_parsed_result():
    model = FakeChatModel(
        {AnalystFindings: AnalystFindings(findings=["demand"], signals=["tickets"])}
    )
    result = await invoke_structured(model, AnalystFindings, "prompt", node="demo")
    assert result.findings == ["demand"]
    assert result.signals == ["tickets"]


async def test_invoke_structured_raises_structured_output_error_on_none():
    # A model that does not support tool/function calling returns None.
    model = FakeChatModel({AnalystFindings: None})
    with pytest.raises(StructuredOutputError, match="tool/function calling"):
        await invoke_structured(model, AnalystFindings, "prompt", node="demo")


async def test_invoke_structured_wraps_provider_error_with_friendly_message():
    model = FakeChatModel({AnalystFindings: RuntimeError("Provider returned error")})
    with pytest.raises(ProviderError, match="Provider returned error") as exc_info:
        await invoke_structured(model, AnalystFindings, "prompt", node="demo")
    # Unknown errors are non-fatal so the node still degrades gracefully.
    assert exc_info.value.fatal is False
    assert exc_info.value.category == ErrorCategory.UNKNOWN.value


async def test_invoke_structured_marks_rate_limit_fatal():
    model = FakeChatModel(
        {AnalystFindings: RuntimeError("Rate limit exceeded: free-models-per-day")}
    )
    with pytest.raises(ProviderError) as exc_info:
        await invoke_structured(model, AnalystFindings, "prompt", node="demo")
    assert exc_info.value.fatal is True
    assert exc_info.value.category == ErrorCategory.RATE_LIMIT.value
