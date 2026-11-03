from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers.constants import TEST_API_KEY


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "amount": "100.50",
        "currency": "RUB",
        "description": "Order #1",
        "metadata": {"order": 1},
        "webhook_url": "https://example.com/hook",
    }
    payload.update(overrides)
    return payload


def _headers() -> dict[str, str]:
    return {"X-API-Key": TEST_API_KEY, "Idempotency-Key": f"metadata-{uuid.uuid4()}"}


async def test_too_large_metadata_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(metadata={"blob": "x" * 70_000}),
        headers=_headers(),
    )

    assert response.status_code == 422


async def test_too_deep_metadata_is_rejected(client: AsyncClient) -> None:
    nested: dict[str, Any] = {}
    cursor = nested
    for _ in range(12):
        child: dict[str, Any] = {}
        cursor["child"] = child
        cursor = child

    response = await client.post(
        "/api/v1/payments",
        json=_payload(metadata=nested),
        headers=_headers(),
    )

    assert response.status_code == 422


async def test_too_many_metadata_keys_are_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(metadata={f"key-{index}": index for index in range(300)}),
        headers=_headers(),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("description", ["", "   ", "\t\n"])
async def test_blank_description_is_rejected(
    client: AsyncClient,
    description: str,
) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(description=description),
        headers=_headers(),
    )

    assert response.status_code == 422


async def test_allowed_metadata_size_is_accepted(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(metadata={"blob": "x" * 60_000}),
        headers=_headers(),
    )

    assert response.status_code == 202
