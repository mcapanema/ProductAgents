"""Tests for the shared structured-output wrapper."""

import pytest

from productagents.agents._llm_call import StructuredOutputError, invoke_structured
from productagents.schemas import AnalystFindings
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


async def test_invoke_structured_reraises_provider_error():
    model = FakeChatModel({AnalystFindings: RuntimeError("Provider returned error")})
    with pytest.raises(RuntimeError, match="Provider returned error"):
        await invoke_structured(model, AnalystFindings, "prompt", node="demo")
