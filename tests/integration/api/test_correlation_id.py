from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.fakes.store import InMemoryStore
from tests.helpers.constants import TEST_API_KEY

PAYLOAD = {
    "amount": "10.00",
    "currency": "USD",
    "description": "Correlated order",
    "metadata": {"order": 42},
    "webhook_url": "https://example.com/hook",
}


def _headers(request_id: str | None = None) -> dict[str, str]:
    headers = {"X-API-Key": TEST_API_KEY, "Idempotency-Key": f"key-{uuid.uuid4()}"}
    if request_id is not None:
        headers["X-Request-ID"] = request_id
    return headers


async def test_provided_request_id_is_echoed_and_stored_in_outbox(
    client: AsyncClient,
    store: InMemoryStore,
) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=PAYLOAD,
        headers=_headers("trace-123"),
    )

    assert response.status_code == 202
    assert response.headers["X-Request-ID"] == "trace-123"
    assert store.outbox[-1].payload["correlation_id"] == "trace-123"


async def test_missing_request_id_is_generated(
    client: AsyncClient,
    store: InMemoryStore,
) -> None:
    response = await client.post("/api/v1/payments", json=PAYLOAD, headers=_headers())

    assert response.status_code == 202
    generated = response.headers["X-Request-ID"]
    assert uuid.UUID(generated)
    assert store.outbox[-1].payload["correlation_id"] == generated


async def test_overlong_request_id_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=PAYLOAD,
        headers=_headers("x" * 129),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("request_id", ["bad id", "tab\tid"])
async def test_invalid_request_id_is_rejected(
    client: AsyncClient,
    request_id: str,
) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=PAYLOAD,
        headers=_headers(request_id),
    )

    assert response.status_code in (400, 422)
