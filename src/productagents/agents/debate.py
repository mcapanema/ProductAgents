"""Structured Advocate-vs-Skeptic debate node.

Runs a configurable number of rounds between an Opportunity Advocate and an
Opportunity Skeptic. Each round the advocate argues first, then the skeptic
rebuts; both see the analyst reports and the debate so far. Each turn is
emitted as a custom stream event for live rendering and collected into a
structured transcript returned in graph state.
"""

from productagents.core.config import env_int
from productagents.core.schemas import (
    AnalystReport,
    DebateArgument,
    DebateTurn,
    Initiative,
)

from productagents.agents._format import (
    format_initiative,
    format_reports_brief,
    format_transcript,
)
from productagents.agents._llm_call import invoke_structured
from productagents.agents._stream import get_writer

NODE_ID = "debate"
ADVOCATE = "advocate"
SKEPTIC = "skeptic"
DEFAULT_DEBATE_ROUNDS = 2

_PERSONA = {
    ADVOCATE: (
        "You are the Opportunity Advocate. You argue that the organization SHOULD "
        "pursue this initiative, emphasizing customer value, business impact, "
        "strategic opportunity, and competitive advantage."
    ),
    SKEPTIC: (
        "You are the Opportunity Skeptic. You argue that the organization should NOT "
        "pursue this initiative, emphasizing opportunity cost, risk, complexity, and "
        "uncertainty."
    ),
}


def get_debate_rounds() -> int:
    """Return the configured number of debate rounds (default 2)."""
    return env_int("PRODUCTAGENTS_DEBATE_ROUNDS", DEFAULT_DEBATE_ROUNDS, minimum=1)


def _prompt(
    side: str,
    initiative: Initiative,
    reports: list[AnalystReport],
    history: list[DebateTurn],
) -> str:
    return (
        f"{_PERSONA[side]}\n\n"
        f"{format_initiative(initiative)}\n\n"
        f"Analyst findings:\n{format_reports_brief(reports)}\n\n"
        f"Debate so far:\n"
        f"{format_transcript(history, empty='(no prior arguments yet)')}\n\n"
        "Make your strongest single argument for your side, directly responding to "
        "the opposing points raised so far."
    )


async def _argue(side: str, state: dict, history: list[DebateTurn], model) -> str:
    result = await invoke_structured(
        model,
        DebateArgument,
        _prompt(side, state["initiative"], state["reports"], history),
        node=NODE_ID,
    )
    return result.argument


async def debate_node(state: dict, model) -> dict:
    writer = get_writer()
    rounds = get_debate_rounds()
    turns: list[DebateTurn] = []
    for rnd in range(1, rounds + 1):
        for side in (ADVOCATE, SKEPTIC):
            writer({"node": NODE_ID, "status": f"round {rnd}: {side} arguing…"})
            try:
                argument = await _argue(side, state, turns, model)
            except Exception as exc:  # noqa: BLE001 - degrade one turn, never crash
                writer({"node": NODE_ID, "error": str(exc)})
                argument = f"({side} unavailable: {exc})"
            turn = DebateTurn(round=rnd, side=side, argument=argument)
            turns.append(turn)
            writer({"node": NODE_ID, "turn": turn.model_dump()})
    return {"debate": turns}
