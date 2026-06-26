from dataclasses import dataclass

from productagents.agents.context import AgentContext
from productagents.agents.recall import recall_node
from productagents.core.models import Initiative


@dataclass
class _FakeLearning:
    lessons: list[str]
    raise_exc: bool = False

    async def relevant_lessons(self, initiative):
        if self.raise_exc:
            raise RuntimeError("boom")
        return self.lessons


def _ctx(learning):
    return AgentContext(model=object(), learning=learning)


async def test_recall_surfaces_lessons_from_service():
    ctx = _ctx(_FakeLearning(["SSO integrations take longer than predicted"]))
    state = {"initiative": Initiative(title="Add SSO", description="Enterprise SSO")}
    result = await recall_node(state, ctx)
    assert result["prior_lessons"] == ["SSO integrations take longer than predicted"]


async def test_recall_empty_when_service_returns_nothing():
    result = await recall_node(
        {"initiative": Initiative(title="X", description="y")}, _ctx(_FakeLearning([]))
    )
    assert result["prior_lessons"] == []


async def test_recall_degrades_on_service_error():
    ctx = _ctx(_FakeLearning([], raise_exc=True))
    result = await recall_node(
        {"initiative": Initiative(title="X", description="y")}, ctx
    )
    assert result["prior_lessons"] == []


async def test_null_learning_default_returns_empty():
    ctx = AgentContext(model=object())
    result = await recall_node(
        {"initiative": Initiative(title="X", description="y")}, ctx
    )
    assert result["prior_lessons"] == []
