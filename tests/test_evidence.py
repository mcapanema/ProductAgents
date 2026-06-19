import json

import pytest

from productagents.evidence import EvidenceError, list_scenarios, load_scenario


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
