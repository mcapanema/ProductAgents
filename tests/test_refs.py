from productagents.core.refs import ExternalRef, SourceRef


def test_manual_source_is_provenance_for_user_created_records():
    s = SourceRef.manual()
    assert s.connector == "manual"
    assert s.vendor_type == "manual"
    assert s.vendor_id == ""
    assert s.url is None


def test_connector_source_round_trips():
    s = SourceRef(
        connector="github",
        vendor_type="issue",
        vendor_id="42",
        url="https://github.com/acme/repo/issues/42",
    )
    assert SourceRef.model_validate_json(s.model_dump_json()) == s


def test_external_ref_fields():
    e = ExternalRef(system="jira", id="PROD-1", url="https://acme.atlassian.net/PROD-1")
    assert e.system == "jira"
    assert e.id == "PROD-1"
