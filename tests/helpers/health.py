from __future__ import annotations

from typing import Any

from dishka import make_async_container
from httpx import ASGITransport, AsyncClient

from payment_service.presentation.api.app import create_app
from tests.fakes.health_provider import HealthProvider

API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY}


async def get_health(
    *,
    session_factory: object,
    broker: object,
    path: str = "/health",
    headers: dict[str, Any] | None = None,
    health_timeout_seconds: float = 1.0,
) -> tuple[int, dict[str, str]]:
    container = make_async_container(
        HealthProvider(
            session_factory,
            broker,
            health_timeout_seconds=health_timeout_seconds,
        )
    )
    app = create_app(container)
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path, headers=HEADERS if headers is None else headers)
    finally:
        await container.close()
    return response.status_code, response.json()
