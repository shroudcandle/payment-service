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


def _headers(idempotency_key: str | None = None) -> dict[str, str]:
    return {
        "X-API-Key": TEST_API_KEY,
        "Idempotency-Key": idempotency_key or f"boundary-{uuid.uuid4()}",
    }


@pytest.mark.parametrize(
    ("amount", "expected_status"),
    [
        ("0.01", 202),
        ("9999999999.99", 202),
        ("10000000000.00", 422),
        ("0.001", 422),
        ("0.00", 422),
        ("-1.00", 422),
        ("NaN", 422),
        ("Infinity", 422),
        ("1e5", 202),
        ("1e-5", 422),
    ],
)
async def test_amount_boundaries(
    client: AsyncClient,
    amount: str,
    expected_status: int,
) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(amount=amount),
        headers=_headers(),
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize("currency", ["RUB", "USD", "EUR"])
async def test_supported_currencies_are_accepted(client: AsyncClient, currency: str) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(currency=currency),
        headers=_headers(),
    )

    assert response.status_code == 202


@pytest.mark.parametrize("currency", ["rub", "USDT", "RUR", ""])
async def test_unsupported_currencies_are_rejected(client: AsyncClient, currency: str) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(currency=currency),
        headers=_headers(),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("length", [1, 255])
async def test_idempotency_key_length_boundaries(client: AsyncClient, length: int) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(),
        headers=_headers("k" * length),
    )

    assert response.status_code == 202


async def test_idempotency_key_over_limit_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(),
        headers=_headers("k" * 256),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("length", [1, 1024])
async def test_description_length_boundaries(client: AsyncClient, length: int) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(description="d" * length),
        headers=_headers(),
    )

    assert response.status_code == 202


@pytest.mark.parametrize("description", ["", "d" * 1025, "nul\x00inside"])
async def test_invalid_descriptions_are_rejected(
    client: AsyncClient,
    description: str,
) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(description=description),
        headers=_headers(),
    )

    assert response.status_code == 422


async def test_metadata_round_trips_nested_json(client: AsyncClient) -> None:
    metadata = {
        "order": 1,
        "paid": True,
        "items": [{"sku": "A", "qty": 2}],
        "nested": {"deep": {"value": 1.5}},
        "note": None,
    }

    created = await client.post(
        "/api/v1/payments",
        json=_payload(metadata=metadata),
        headers=_headers(),
    )
    payment_id = created.json()["payment_id"]
    response = await client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert created.status_code == 202
    assert response.status_code == 200
    assert response.json()["metadata"] == metadata


async def test_null_metadata_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(metadata=None),
        headers=_headers(),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "webhook_url",
    [
        "https://example.com:8443/hook?token=abc#section",
        "http://127.0.0.1:9000/hook",
    ],
)
async def test_webhook_url_variants_are_accepted(
    client: AsyncClient,
    webhook_url: str,
) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(webhook_url=webhook_url),
        headers=_headers(),
    )

    assert response.status_code == 202


@pytest.mark.parametrize(
    "webhook_url",
    ["ftp://example.com/hook", "file:///etc/passwd", "https://", "not-a-url"],
)
async def test_invalid_webhook_urls_are_rejected(
    client: AsyncClient,
    webhook_url: str,
) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(webhook_url=webhook_url),
        headers=_headers(),
    )

    assert response.status_code == 422
