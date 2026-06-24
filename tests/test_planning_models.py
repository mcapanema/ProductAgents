from productagents.core.models.planning import Feature, Initiative, RoadmapItem
from productagents.core.refs import SourceRef


def test_user_typed_initiative_still_works_with_manual_provenance():
    init = Initiative(title="Add SSO", description="Enterprise single sign-on")
    assert init.title == "Add SSO"
    assert init.description == "Enterprise single sign-on"
    assert init.source.connector == "manual"  # back-compat for the TUI call site
    assert init.status is None


def test_initiative_round_trips_through_json():
    init = Initiative(title="t", description="d")
    assert Initiative.model_validate_json(init.model_dump_json()) == init


def test_synced_initiative_carries_real_provenance():
    init = Initiative(
        title="Imported",
        description="from github",
        source=SourceRef(connector="github", vendor_type="issue", vendor_id="7"),
        status="planned",
    )
    assert init.source.connector == "github"
    assert init.status == "planned"


def test_feature_and_roadmap_cross_reference_initiative():
    init = Initiative(title="t", description="d")
    feat = Feature(name="SAML flow", initiative_id=init.id)
    item = RoadmapItem(title="Q3 SSO", initiative_id=init.id, quarter="2026-Q3")
    assert feat.initiative_id == init.id
    assert item.quarter == "2026-Q3"
    assert feat.status == "idea"
