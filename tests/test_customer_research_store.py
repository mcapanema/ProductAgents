from productagents.agents.customer_research import customer_research_node
from productagents.core.models import (
    AnalystFindings,
    CustomerFeedback,
    Evidence,
    Initiative,
)
from productagents.knowledge import FeedbackService
from tests.fakes import fake_context
from tests.knowledge_fakes import FakeRepository


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "evidence": Evidence(
            scenario="sample",
            customer_feedback="SCENARIO feedback text",
            product_analytics={},
        ),
    }


def _model():
    # Captures the prompt the model was asked to reason over.
    captured = {}

    class Capturing:
        def with_structured_output(self, schema, **_):
            class _Call:
                async def ainvoke(self, prompt):
                    captured["prompt"] = prompt
                    return AnalystFindings(findings=["f"], signals=["s"])

            return _Call()

    return Capturing(), captured


async def test_uses_store_feedback_when_present():
    model, captured = _model()
    feedback = FeedbackService(
        FakeRepository([CustomerFeedback(body="STORE: please add SSO")])
    )
    result = await customer_research_node(
        _state(), fake_context(model, feedback=feedback)
    )
    assert result["reports"][0].failed is False
    assert "STORE: please add SSO" in captured["prompt"]
    assert "SCENARIO feedback text" not in captured["prompt"]


async def test_falls_back_to_scenario_when_store_empty():
    model, captured = _model()
    feedback = FeedbackService(FakeRepository([]))  # empty store
    await customer_research_node(_state(), fake_context(model, feedback=feedback))
    assert "SCENARIO feedback text" in captured["prompt"]


async def test_falls_back_to_scenario_when_store_errors():
    model, captured = _model()

    class Exploding:
        async def search(self, query):
            raise RuntimeError("table missing")

    result = await customer_research_node(
        _state(), fake_context(model, feedback=Exploding())
    )
    assert "SCENARIO feedback text" in captured["prompt"]
    assert result["reports"][0].failed is False  # store error must NOT fail the report
