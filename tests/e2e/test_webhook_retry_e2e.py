from __future__ import annotations

import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.domain.payment import PaymentStatus
from payment_service.infrastructure.persistence.tables import PaymentTable
from tests.e2e.constants import API_KEY
from tests.e2e.webhook_receiver import WebhookReceiver
from tests.helpers.network import wait_for


async def test_webhook_is_retried_through_broker_until_delivered(
    api_server: str,
    worker: None,
    db_session: AsyncSession,
    webhook_receiver: WebhookReceiver,
) -> None:
    _ = worker
    webhook_receiver.failures_remaining = 2
    idempotency_key = f"e2e-{uuid.uuid4()}"
    headers = {"X-API-Key": API_KEY, "Idempotency-Key": idempotency_key}
    payload: dict[str, Any] = {
        "amount": "42.00",
        "currency": "RUB",
        "description": "Retry order",
        "metadata": {"order": "e2e"},
        "webhook_url": webhook_receiver.url,
    }

    async with httpx.AsyncClient(base_url=api_server, timeout=10.0) as client:
        created = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert created.status_code == 202
        payment_id = created.json()["payment_id"]

    async def webhook_delivered() -> bool:
        return len(webhook_receiver.received) == 1

    await wait_for(
        webhook_delivered,
        timeout=40.0,
        message="webhook was not delivered after broker retry",
    )

    assert webhook_receiver.attempts == 3
    webhook = webhook_receiver.received[0]
    assert webhook["payment_id"] == payment_id
    assert webhook["status"] == PaymentStatus.SUCCEEDED.value

    db_session.expire_all()
    payment = (
        await db_session.execute(
            select(PaymentTable).where(PaymentTable.id == uuid.UUID(payment_id))
        )
    ).scalar_one()
    assert payment.status == PaymentStatus.SUCCEEDED.value
    assert payment.processed_at is not None
