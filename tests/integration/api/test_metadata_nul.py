from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers.constants import TEST_API_KEY


def _payload(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "amount": "10.00",
        "currency": "RUB",
        "description": "Metadata order",
        "metadata": metadata,
        "webhook_url": "https://example.com/hook",
    }


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": TEST_API_KEY,
        "Idempotency-Key": f"metadata-{uuid.uuid4()}",
    }


@pytest.mark.parametrize(
    "metadata",
    [
        {"key\x00": "value"},
        {"key": "value\x00"},
        {"nested": {"key": "\x00"}},
        {"items": [{"sku": "A"}, {"sku": "\x00"}]},
    ],
)
async def test_metadata_with_nul_is_rejected(
    client: AsyncClient,
    metadata: dict[str, Any],
) -> None:
    response = await client.post(
        "/api/v1/payments",
        json=_payload(metadata),
        headers=_headers(),
    )

    assert response.status_code == 422
