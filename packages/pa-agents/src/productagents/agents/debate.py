"""Structured Advocate-vs-Skeptic debate node.

Runs a configurable number of rounds between an Opportunity Advocate and an
Opportunity Skeptic. Each round the advocate argues first, then the skeptic
rebuts; both see the analyst reports and the debate so far. Each turn is
emitted as a custom stream event for live rendering and collected into a
structured transcript returned in graph state.
"""

from productagents.agents._format import (
    format_initiative,
    format_reports_brief,
    format_transcript,
)
from productagents.agents._llm_call import invoke_structured
from productagents.agents._stream import get_writer
from productagents.agents.prompts import PromptStore
from productagents.agents.stream_events import (
    TURN,
    emit_error,
    emit_payload,
    emit_status,
)
from productagents.core.config import env_int
from productagents.core.models import (
    AnalystReport,
    DebateArgument,
    DebateTurn,
    Initiative,
)

NODE_ID = "debate"
ADVOCATE = "advocate"
SKEPTIC = "skeptic"
DEFAULT_DEBATE_ROUNDS = 2


def get_debate_rounds() -> int:
    """Return the configured number of debate rounds (default 2)."""
    return env_int("PRODUCTAGENTS_DEBATE_ROUNDS", DEFAULT_DEBATE_ROUNDS, minimum=1)


def _prompt(
    side: str,
    initiative: Initiative,
    reports: list[AnalystReport],
    history: list[DebateTurn],
    prompts: PromptStore,
) -> str:
    return prompts.render(
        "debate",
        persona=prompts.get(f"debate.{side}"),
        initiative=format_initiative(initiative),
        reports=format_reports_brief(reports),
        history=format_transcript(history, empty="(no prior arguments yet)"),
    )


async def _argue(
    side: str, state: dict, history: list[DebateTurn], model, prompts: PromptStore
) -> str:
    result = await invoke_structured(
        model,
        DebateArgument,
        _prompt(side, state["initiative"], state["reports"], history, prompts),
        node=NODE_ID,
    )
    return result.argument


async def debate_node(state: dict, model, prompts: PromptStore | None = None) -> dict:
    store = prompts or PromptStore()
    writer = get_writer()
    rounds = get_debate_rounds()
    turns: list[DebateTurn] = []
    for rnd in range(1, rounds + 1):
        for side in (ADVOCATE, SKEPTIC):
            writer(emit_status(NODE_ID, f"round {rnd}: {side} arguing…"))
            try:
                argument = await _argue(side, state, turns, model, store)
            except Exception as exc:  # noqa: BLE001 - degrade one turn, never crash
                writer(emit_error(NODE_ID, str(exc)))
                argument = f"({side} unavailable: {exc})"
            turn = DebateTurn(round=rnd, side=side, argument=argument)
            turns.append(turn)
            writer(emit_payload(NODE_ID, TURN, turn))
    return {"debate": turns}
