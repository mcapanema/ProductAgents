from typing import get_args

import pytest
from pydantic import BaseModel, ValidationError

from productagents.core.enums import (
    DebateSide,
    DecidedBy,
    IncidentStatus,
    Priority,
    RiskLevel,
    Sentiment,
    Verdict,
)


def test_v1_vocabularies_unchanged():
    assert set(get_args(Verdict)) == {"approve", "reject", "request_analysis"}
    assert set(get_args(RiskLevel)) == {"low", "medium", "high"}
    assert set(get_args(DebateSide)) == {"advocate", "skeptic"}
    assert set(get_args(DecidedBy)) == {"ai", "human"}


def test_new_vocabularies_present():
    assert set(get_args(Priority)) == {"low", "medium", "high", "critical"}
    assert set(get_args(Sentiment)) == {"positive", "neutral", "negative"}
    assert "investigating" in get_args(IncidentStatus)


def test_literal_is_enforced_by_pydantic():
    class M(BaseModel):
        p: Priority

    assert M(p="high").p == "high"
    with pytest.raises(ValidationError):
        M(p="urgent")
