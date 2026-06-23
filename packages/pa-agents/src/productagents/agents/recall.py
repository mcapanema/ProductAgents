"""Recall node: surface lessons from relevant past decisions.

This is the injection half of Outcome Learning. It runs in parallel from START,
reads the prior decisions and outcomes seeded into state at the UI boundary,
selects the lessons from the most similar past initiatives, and writes them to
`prior_lessons` for the strategist to consume. It is model-free (retrieval is
deterministic lexical matching) and degrades to an empty list on any error.
"""

from productagents.agents._stream import get_writer
from productagents.memory import select_relevant_lessons

NODE_ID = "recall"


async def recall_node(state: dict) -> dict:
    writer = get_writer()
    writer({"node": NODE_ID, "status": "recalling lessons from past decisions…"})
    try:
        lessons = select_relevant_lessons(
            state["initiative"],
            state.get("portfolio", []),
            state.get("outcomes", []),
        )
        writer({"node": NODE_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "status": f"failed: {exc}"})
        lessons = []
    return {"prior_lessons": lessons}
