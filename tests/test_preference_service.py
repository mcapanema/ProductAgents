import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from productagents.platform.preference_service import PreferenceService


@pytest.fixture
def engine():
    return create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)


async def test_roundtrip_and_whitelist(engine):
    svc = PreferenceService(engine=engine)
    assert await svc.all() == {}
    assert await svc.set("theme", "dark") == {"theme": "dark"}
    assert await svc.all() == {"theme": "dark"}
    with pytest.raises(ValueError, match="unknown preference"):
        await svc.set("model", "sneaky")  # config must never route through prefs
