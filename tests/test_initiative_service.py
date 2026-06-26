"""InitiativeService searches the decision spine by status and free text."""

from productagents.core.models import Initiative
from productagents.knowledge.services.initiative_service import (
    InitiativeQuery,
    InitiativeService,
)
from tests.knowledge_fakes import FakeRepository


def _corpus() -> list[Initiative]:
    return [
        Initiative(title="Add SSO", description="Enterprise login", status="proposed"),
        Initiative(title="Billing v2", description="Usage-based", status="shipped"),
        Initiative(title="SSO hardening", description="MFA", status="in_progress"),
    ]


async def test_search_by_text_matches_title_and_description():
    svc = InitiativeService(FakeRepository(_corpus()))
    page = await svc.search(InitiativeQuery(text="sso"))
    assert sorted(i.title for i in page.items) == ["Add SSO", "SSO hardening"]
    assert page.total == 2


async def test_search_by_status():
    svc = InitiativeService(FakeRepository(_corpus()))
    page = await svc.search(InitiativeQuery(status="shipped"))
    assert [i.title for i in page.items] == ["Billing v2"]


async def test_text_matches_description_only():
    svc = InitiativeService(FakeRepository(_corpus()))
    page = await svc.search(InitiativeQuery(text="usage-based"))
    assert [i.title for i in page.items] == ["Billing v2"]
