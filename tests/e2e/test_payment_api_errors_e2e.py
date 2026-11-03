from __future__ import annotations

import uuid
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.infrastructure.persistence.tables import PaymentTable
from tests.e2e.constants import API_KEY


async def test_api_rejects_unauthorized_invalid_and_unknown_requests(
    api_server: str,
    db_session: AsyncSession,
) -> None:
    headers = {"X-API-Key": API_KEY, "Idempotency-Key": f"e2e-{uuid.uuid4()}"}
    payload: dict[str, Any] = {
        "amount": "42.00",
        "currency": "RUB",
        "description": "Invalid requests",
        "metadata": {"order": "e2e"},
        "webhook_url": "https://example.com/hook",
    }

    async with httpx.AsyncClient(base_url=api_server, timeout=10.0) as client:
        missing_key = await client.post(
            "/api/v1/payments",
            json=payload,
            headers={"Idempotency-Key": headers["Idempotency-Key"]},
        )
        assert missing_key.status_code == 401
        assert missing_key.json()["detail"] == "Invalid or missing API key"

        wrong_key = await client.post(
            "/api/v1/payments",
            json=payload,
            headers={**headers, "X-API-Key": "wrong"},
        )
        assert wrong_key.status_code == 401

        invalid_amount = await client.post(
            "/api/v1/payments",
            json={**payload, "amount": "-10.00"},
            headers=headers,
        )
        assert invalid_amount.status_code == 422

        missing_id = uuid.uuid4()
        unknown = await client.get(
            f"/api/v1/payments/{missing_id}",
            headers={"X-API-Key": API_KEY},
        )
        assert unknown.status_code == 404
        assert unknown.json()["detail"] == f"Payment {missing_id} not found"

    payments_count = await db_session.scalar(select(func.count()).select_from(PaymentTable))
    assert payments_count == 0
