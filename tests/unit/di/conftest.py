from __future__ import annotations

import pytest
from dishka import AsyncContainer

from payment_service.di import make_container


@pytest.fixture
async def container(monkeypatch: pytest.MonkeyPatch) -> AsyncContainer:
    monkeypatch.setenv("API_KEY", "test-api-key")
    async_container = make_container()
    yield async_container
    await async_container.close()
