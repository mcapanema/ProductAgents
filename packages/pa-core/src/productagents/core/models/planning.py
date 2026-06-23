"""Planning context: the work the product team proposes and tracks."""

from pydantic import Field

from productagents.core.enums import FeatureStatus, InitiativeStatus, Priority
from productagents.core.ids import FeatureId, InitiativeId, RoadmapItemId, new_id
from productagents.core.models._base import CanonicalModel


class Initiative(CanonicalModel):
    """A product proposal under evaluation.

    Manually created (user-typed) initiatives carry `SourceRef.manual()`; ones
    synced from a connector carry that connector's provenance. Agents reason over
    `title`/`description`/`status`/etc., never over `source`.
    """

    id: InitiativeId = Field(default_factory=lambda: InitiativeId(new_id()))
    title: str
    description: str
    status: InitiativeStatus | None = None
    priority: Priority | None = None
    owner: str | None = None
    target_quarter: str | None = None


class Feature(CanonicalModel):
    """A discrete capability, optionally rolling up to an Initiative."""

    id: FeatureId = Field(default_factory=lambda: FeatureId(new_id()))
    name: str
    description: str = ""
    status: FeatureStatus = "idea"
    initiative_id: InitiativeId | None = None


class RoadmapItem(CanonicalModel):
    """A scheduled commitment on the roadmap."""

    id: RoadmapItemId = Field(default_factory=lambda: RoadmapItemId(new_id()))
    title: str
    initiative_id: InitiativeId | None = None
    quarter: str | None = None
    status: str | None = None
