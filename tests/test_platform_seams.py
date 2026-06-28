"""Assert platform seam modules re-export the right agent-layer symbols."""

from productagents.platform.evidence import (
    EvidenceError,
    collect_evidence,
    load_scenario,
)
from productagents.platform.llm import DEFAULT_MODEL, get_model
from productagents.platform.reflection import reflect


def test_collect_evidence_is_agents_collect_evidence():
    from productagents.agents.evidence import collect_evidence as a

    assert collect_evidence is a


def test_load_scenario_is_agents_load_scenario():
    from productagents.agents.evidence import load_scenario as a

    assert load_scenario is a


def test_evidence_error_is_agents_evidence_error():
    from productagents.agents.evidence import EvidenceError as a

    assert EvidenceError is a


def test_get_model_is_agents_get_model():
    from productagents.agents.llm import get_model as a

    assert get_model is a


def test_default_model_is_agents_default_model():
    from productagents.agents.llm import DEFAULT_MODEL as a

    assert DEFAULT_MODEL is a


def test_reflect_is_agents_reflect():
    from productagents.agents.reflection import reflect as a

    assert reflect is a
