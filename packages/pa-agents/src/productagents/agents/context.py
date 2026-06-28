"""The capability bundle injected into graph nodes.

`recall` taught the graph to take read-side state at the boundary; `AgentContext`
generalizes that to *capabilities*: nodes get the chat model plus the Knowledge
Services they are allowed to use, never a session, repository, or connector. Tests
inject fakes, exactly as they do for the model.
"""

from dataclasses import dataclass, field
from typing import Protocol

from productagents.agents.prompts import PromptStore
from productagents.core.models import CustomerFeedback, DecisionRecord, Initiative
from productagents.knowledge.services._page import Page
from productagents.knowledge.services.feedback_service import FeedbackQuery


class FeedbackReader(Protocol):
    """The slice of the feedback service the Customer Research analyst may use."""

    async def search(self, query: FeedbackQuery) -> Page[CustomerFeedback]: ...


class _NullFeedback:
    """Default reader for a context with no store wired (tests, bare-model graphs).

    Returns an empty page so the Customer Research node degrades to its scenario
    evidence — identical to pre-Phase-5 behavior.
    """

    async def search(self, query: FeedbackQuery) -> Page[CustomerFeedback]:
        return Page(items=[], total=0, limit=query.limit, offset=query.offset)


class LessonReader(Protocol):
    """The slice of the LearningService the recall and governance nodes may use."""

    async def relevant_lessons(self, initiative: Initiative) -> list[str]: ...

    async def decisions(self) -> list[DecisionRecord]: ...


class _NullLearning:
    """Default for a context with no memory store wired (tests, bare-model graphs)."""

    async def relevant_lessons(self, initiative: Initiative) -> list[str]:
        return []

    async def decisions(self) -> list[DecisionRecord]:
        return []


@dataclass(frozen=True)
class AgentContext:
    """Model + the service slices nodes may use. The platform's DI seam.

    Only `feedback` is carried today because Customer Research is the only analyst
    with a live canonical source. `initiatives`/`metrics` slices join this bundle
    when an analyst actually consumes them — least privilege, no empty fields.
    """

    model: object
    feedback: FeedbackReader = field(default_factory=_NullFeedback)
    learning: LessonReader = field(default_factory=_NullLearning)
    prompts: PromptStore = field(default_factory=PromptStore)
