from productagents.agents.debate import debate_node, get_debate_rounds
from productagents.core.schemas import AnalystReport, DebateArgument, Initiative
from tests.fakes import FakeChatModel


def _state():
    return {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "reports": [
            AnalystReport(
                analyst="customer_research",
                role="Customer Research Analyst",
                findings=["demand"],
                signals=["tickets"],
            )
        ],
    }


def test_get_debate_rounds_default(monkeypatch):
    monkeypatch.delenv("PRODUCTAGENTS_DEBATE_ROUNDS", raising=False)
    assert get_debate_rounds() == 2


def test_get_debate_rounds_env_override(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "3")
    assert get_debate_rounds() == 3


def test_get_debate_rounds_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "not-a-number")
    assert get_debate_rounds() == 2
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "0")
    assert get_debate_rounds() == 2


async def test_debate_node_produces_ordered_turns(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "2")
    model = FakeChatModel({DebateArgument: DebateArgument(argument="my point")})
    result = await debate_node(_state(), model)
    turns = result["debate"]
    assert [(t.round, t.side) for t in turns] == [
        (1, "advocate"),
        (1, "skeptic"),
        (2, "advocate"),
        (2, "skeptic"),
    ]
    assert all(t.argument == "my point" for t in turns)


async def test_debate_node_degrades_on_failure(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    model = FakeChatModel({DebateArgument: RuntimeError("LLM down")})
    result = await debate_node(_state(), model)
    turns = result["debate"]
    assert len(turns) == 2
    assert "unavailable" in turns[0].argument
    assert turns[0].side == "advocate"


async def test_debate_degrades_when_model_returns_none(monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_DEBATE_ROUNDS", "1")
    model = FakeChatModel({DebateArgument: None})
    state = {
        "initiative": Initiative(title="Add SSO", description="Enterprise SSO"),
        "reports": [],
    }
    result = await debate_node(state, model)
    # One round → advocate + skeptic, both unavailable placeholders, not a crash.
    assert len(result["debate"]) == 2
    assert all("unavailable" in turn.argument for turn in result["debate"])
