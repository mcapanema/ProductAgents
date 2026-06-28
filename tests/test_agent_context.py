from productagents.agents.context import AgentContext
from productagents.agents.prompts import PromptStore
from productagents.knowledge import FeedbackQuery


async def test_default_feedback_is_empty():
    ctx = AgentContext(model="m")
    page = await ctx.feedback.search(FeedbackQuery())
    assert page.items == []
    assert page.total == 0


async def test_carries_provided_feedback():
    class StubFeedback:
        async def search(self, query):
            return "PAGE"

    ctx = AgentContext(model="m", feedback=StubFeedback())
    assert ctx.model == "m"
    assert await ctx.feedback.search(FeedbackQuery()) == "PAGE"


def test_agent_context_defaults_to_a_prompt_store():
    ctx = AgentContext(model=object())
    assert isinstance(ctx.prompts, PromptStore)
