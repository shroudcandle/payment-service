from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.helpers.constants import TEST_API_KEY

API_KEY_HEADERS = {"X-API-Key": TEST_API_KEY}
IDEMPOTENCY_HEADERS = {**API_KEY_HEADERS, "Idempotency-Key": "pay-1"}
PAYLOAD = {
    "amount": "100.50",
    "currency": "RUB",
    "description": "Order #1",
    "metadata": {"order": 1},
    "webhook_url": "https://example.com/hook",
}


async def test_create_payment_requires_api_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=PAYLOAD,
        headers={"Idempotency-Key": "pay-1"},
    )

    assert response.status_code == 401


async def test_create_payment_requires_idempotency_key(client: AsyncClient) -> None:
    response = await client.post("/api/v1/payments", json=PAYLOAD, headers=API_KEY_HEADERS)

    assert response.status_code == 422


async def test_create_payment_returns_accepted(client: AsyncClient) -> None:
    response = await client.post("/api/v1/payments", json=PAYLOAD, headers=IDEMPOTENCY_HEADERS)

    assert response.status_code == 202
    body = response.json()
    assert uuid.UUID(body["payment_id"])
    assert body["status"] == "pending"


async def test_create_payment_is_idempotent(client: AsyncClient) -> None:
    first = await client.post("/api/v1/payments", json=PAYLOAD, headers=IDEMPOTENCY_HEADERS)
    second = await client.post("/api/v1/payments", json=PAYLOAD, headers=IDEMPOTENCY_HEADERS)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["payment_id"] == second.json()["payment_id"]


async def test_create_payment_conflicts_on_payload_mismatch(client: AsyncClient) -> None:
    await client.post("/api/v1/payments", json=PAYLOAD, headers=IDEMPOTENCY_HEADERS)

    response = await client.post(
        "/api/v1/payments",
        json={**PAYLOAD, "amount": "101.00"},
        headers=IDEMPOTENCY_HEADERS,
    )

    assert response.status_code == 409


async def test_get_payment_returns_details(client: AsyncClient) -> None:
    created = await client.post("/api/v1/payments", json=PAYLOAD, headers=IDEMPOTENCY_HEADERS)
    payment_id = created.json()["payment_id"]

    response = await client.get(f"/api/v1/payments/{payment_id}", headers=API_KEY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == payment_id
    assert body["amount"] == "100.50"
    assert body["status"] == "pending"


async def test_get_unknown_payment_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/payments/{uuid.uuid4()}", headers=API_KEY_HEADERS)

    assert response.status_code == 404
