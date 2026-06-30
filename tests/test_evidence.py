import json
from pathlib import Path

import pytest

from productagents.agents.evidence import EvidenceError, list_scenarios, load_scenario
from productagents.core.models import Evidence


class _RemoteSource:
    def __init__(self, spec: str):
        self.spec = spec

    def collect(self) -> Evidence:
        return Evidence(
            scenario=self.spec,
            customer_feedback="remote feedback",
            product_analytics={},
            market_intelligence="",
            business_metrics={},
            technical_context="",
            sources=[],
        )


def _remote_resolver(spec: str, base_dir: Path | None):
    return _RemoteSource(spec) if spec.startswith("remote:") else None


def test_loads_bundled_sample_scenario():
    evidence = load_scenario("sample")
    assert evidence.scenario == "sample"
    assert isinstance(evidence.customer_feedback, str)
    assert evidence.customer_feedback.strip() != ""
    assert isinstance(evidence.product_analytics, dict)


def test_sample_listed_in_scenarios():
    assert "sample" in list_scenarios()


def test_missing_scenario_raises(tmp_path):
    with pytest.raises(EvidenceError):
        load_scenario("does-not-exist", base_dir=tmp_path)


def test_malformed_analytics_raises(tmp_path):
    scenario = tmp_path / "broken"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("ok")
    (scenario / "product_analytics.json").write_text("{not valid json")
    with pytest.raises(EvidenceError):
        load_scenario("broken", base_dir=tmp_path)


def test_loads_from_custom_base_dir(tmp_path):
    scenario = tmp_path / "custom"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("feedback text")
    (scenario / "product_analytics.json").write_text(json.dumps({"dau": 100}))
    evidence = load_scenario("custom", base_dir=tmp_path)
    assert evidence.customer_feedback == "feedback text"
    assert evidence.product_analytics == {"dau": 100}


def test_sample_scenario_loads_new_evidence_fields():
    evidence = load_scenario("sample")
    assert isinstance(evidence.market_intelligence, str)
    assert evidence.market_intelligence.strip() != ""
    assert isinstance(evidence.business_metrics, dict)
    assert evidence.business_metrics != {}
    assert isinstance(evidence.technical_context, str)
    assert evidence.technical_context.strip() != ""


def test_scenario_without_new_files_uses_defaults(tmp_path):
    scenario = tmp_path / "minimal"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("feedback text")
    (scenario / "product_analytics.json").write_text(json.dumps({"dau": 100}))
    evidence = load_scenario("minimal", base_dir=tmp_path)
    assert evidence.market_intelligence == ""
    assert evidence.business_metrics == {}
    assert evidence.technical_context == ""


def test_malformed_business_metrics_raises(tmp_path):
    scenario = tmp_path / "broken-biz"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("ok")
    (scenario / "product_analytics.json").write_text(json.dumps({"x": 1}))
    (scenario / "business_metrics.json").write_text("{not valid json")
    with pytest.raises(EvidenceError):
        load_scenario("broken-biz", base_dir=tmp_path)


def test_scenario_source_populates_provenance():
    from productagents.agents.evidence import ScenarioSource

    evidence = ScenarioSource("sample").collect()
    assert evidence.scenario == "sample"
    by_field = {ref.field: ref for ref in evidence.sources}
    # Required fields always have provenance.
    assert by_field["customer_feedback"].source == "scenario:sample"
    assert by_field["customer_feedback"].location.endswith("customer_feedback.md")
    assert by_field["product_analytics"].location.endswith("product_analytics.json")


def test_load_scenario_still_works_and_has_provenance():
    # Backward-compatible wrapper keeps returning Evidence, now with sources.
    evidence = load_scenario("sample")
    assert evidence.customer_feedback.strip() != ""
    assert any(ref.field == "customer_feedback" for ref in evidence.sources)


def test_scenario_source_omits_provenance_for_absent_optional_files(tmp_path):
    from productagents.agents.evidence import ScenarioSource

    scenario = tmp_path / "minimal"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("feedback text")
    (scenario / "product_analytics.json").write_text('{"dau": 100}')
    evidence = ScenarioSource("minimal", base_dir=tmp_path).collect()
    fields = {ref.field for ref in evidence.sources}
    assert fields == {"customer_feedback", "product_analytics"}


def test_directory_source_reads_arbitrary_folder(tmp_path):
    from productagents.agents.evidence import DirectorySource

    folder = tmp_path / "q3-data"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("users want SSO")
    (folder / "product_analytics.json").write_text('{"dau": 4200}')
    (folder / "technical_context.md").write_text("auth service is legacy")

    evidence = DirectorySource(folder).collect()
    assert evidence.scenario == "q3-data"
    assert evidence.customer_feedback == "users want SSO"
    assert evidence.product_analytics == {"dau": 4200}
    assert evidence.technical_context == "auth service is legacy"
    by_field = {ref.field: ref for ref in evidence.sources}
    assert by_field["customer_feedback"].source == f"directory:{folder}"
    assert "technical_context" in by_field
    assert "market_intelligence" not in by_field  # absent optional file → no ref


def test_directory_source_missing_dir_raises(tmp_path):
    from productagents.agents.evidence import DirectorySource

    with pytest.raises(EvidenceError):
        DirectorySource(tmp_path / "nope").collect()


def test_directory_source_missing_required_file_raises(tmp_path):
    from productagents.agents.evidence import DirectorySource

    folder = tmp_path / "incomplete"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("feedback only")
    with pytest.raises(EvidenceError):
        DirectorySource(folder).collect()


def test_collect_evidence_defaults_to_sample():
    from productagents.agents.evidence import collect_evidence

    evidence = collect_evidence(None)
    assert evidence.scenario == "sample"
    assert evidence.sources
    assert evidence.sources[0].source == "scenario:sample"


def test_collect_evidence_resolves_known_scenario(tmp_path):
    from productagents.agents.evidence import collect_evidence

    scenario = tmp_path / "alpha"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("f")
    (scenario / "product_analytics.json").write_text('{"x": 1}')
    evidence = collect_evidence("alpha", base_dir=tmp_path)
    assert evidence.scenario == "alpha"
    assert evidence.sources[0].source == "scenario:alpha"


def test_collect_evidence_resolves_directory_path(tmp_path):
    from productagents.agents.evidence import collect_evidence

    folder = tmp_path / "loose-folder"
    folder.mkdir()
    (folder / "customer_feedback.md").write_text("f")
    (folder / "product_analytics.json").write_text('{"x": 1}')
    evidence = collect_evidence(str(folder))
    assert evidence.scenario == "loose-folder"
    assert evidence.sources[0].source == f"directory:{folder}"


def test_collect_evidence_unknown_spec_raises():
    from productagents.agents.evidence import collect_evidence

    with pytest.raises(EvidenceError):
        collect_evidence("definitely-not-a-scenario-or-path")


def test_collect_evidence_uses_registered_resolver(monkeypatch):
    from importlib.metadata import EntryPoint

    from productagents.agents import evidence as ev

    ep = EntryPoint(
        name="remote",
        value="tests.test_evidence:_remote_resolver",
        group="productagents.evidence_sources",
    )
    monkeypatch.setattr(ev, "entry_points", lambda group: [ep])
    result = ev.collect_evidence("remote:thing")
    assert result.scenario == "remote:thing"
    assert result.customer_feedback == "remote feedback"


def test_collect_evidence_builtins_take_priority(monkeypatch, tmp_path):
    from importlib.metadata import EntryPoint

    from productagents.agents import evidence as ev

    scenario = tmp_path / "alpha"
    scenario.mkdir()
    (scenario / "customer_feedback.md").write_text("f")
    (scenario / "product_analytics.json").write_text('{"x": 1}')
    ep = EntryPoint(  # a greedy resolver that would claim everything
        name="greedy",
        value="tests.test_evidence:_remote_resolver",
        group="productagents.evidence_sources",
    )
    monkeypatch.setattr(ev, "entry_points", lambda group: [ep])
    result = ev.collect_evidence("alpha", base_dir=tmp_path)
    # The built-in ScenarioSource wins for a known scenario name.
    assert result.sources[0].source == "scenario:alpha"


def test_collect_evidence_skips_broken_resolver_entry_point(monkeypatch):
    from importlib.metadata import EntryPoint

    from productagents.agents import evidence as ev

    bad = EntryPoint(
        name="broken",
        value="tests.test_evidence:does_not_exist",
        group="productagents.evidence_sources",
    )
    monkeypatch.setattr(ev, "entry_points", lambda group: [bad])
    with pytest.raises(EvidenceError):  # broken plugin skipped → falls through to error
        ev.collect_evidence("definitely-not-a-scenario-or-path")
