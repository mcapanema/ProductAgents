"""Recall node: surface lessons from relevant past decisions.

The injection half of Outcome Learning. It runs in parallel from START and asks
the LearningService (via ``ctx.learning``) for the lessons of the past decisions
most similar to the current initiative — lexical + semantic hybrid retrieval over
the real decision store. Model-free; degrades to an empty list on any error.
"""

from productagents.agents._stream import get_writer

NODE_ID = "recall"


async def recall_node(state: dict, ctx) -> dict:
    writer = get_writer()
    writer({"node": NODE_ID, "status": "recalling lessons from past decisions…"})
    try:
        lessons = await ctx.learning.relevant_lessons(state["initiative"])
        writer({"node": NODE_ID, "status": "done"})
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the graph
        writer({"node": NODE_ID, "status": f"failed: {exc}"})
        lessons = []
    return {"prior_lessons": lessons}
