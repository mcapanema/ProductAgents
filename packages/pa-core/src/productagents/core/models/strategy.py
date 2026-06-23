"""Strategy context: objectives and the key results that measure them."""

from pydantic import Field

from productagents.core.ids import KeyResultId, ObjectiveId, new_id
from productagents.core.models._base import CanonicalModel


class Objective(CanonicalModel):
    """A strategic objective the product is steering toward."""

    id: ObjectiveId = Field(default_factory=lambda: ObjectiveId(new_id()))
    title: str
    description: str = ""
    period: str | None = None
    owner: str | None = None


class KeyResult(CanonicalModel):
    """A measurable result for an Objective."""

    id: KeyResultId = Field(default_factory=lambda: KeyResultId(new_id()))
    description: str
    objective_id: ObjectiveId | None = None
    target: float | None = None
    current: float | None = None
    unit: str | None = None
