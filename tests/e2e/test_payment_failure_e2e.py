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


async def test_failed_gateway_marks_payment_failed_and_notifies_receiver(
    infrastructure: str,
    gateway_failure: None,
    api_server: str,
    worker: None,
    db_session: AsyncSession,
    webhook_receiver: WebhookReceiver,
) -> None:
    _ = infrastructure, gateway_failure, worker
    idempotency_key = f"e2e-{uuid.uuid4()}"
    headers = {"X-API-Key": API_KEY, "Idempotency-Key": idempotency_key}
    payload: dict[str, Any] = {
        "amount": "17.00",
        "currency": "USD",
        "description": "Declined order",
        "metadata": {"order": "failed"},
        "webhook_url": webhook_receiver.url,
    }

    async with httpx.AsyncClient(base_url=api_server, timeout=10.0) as client:
        created = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert created.status_code == 202
        payment_id = created.json()["payment_id"]

        async def webhook_delivered() -> bool:
            return len(webhook_receiver.received) == 1

        await wait_for(webhook_delivered, timeout=30.0, message="webhook was not delivered")

        details = await client.get(
            f"/api/v1/payments/{payment_id}",
            headers={"X-API-Key": API_KEY},
        )

    assert details.json()["status"] == PaymentStatus.FAILED.value
    assert details.json()["processed_at"] is not None

    db_session.expire_all()
    payment = (
        await db_session.execute(
            select(PaymentTable).where(PaymentTable.id == uuid.UUID(payment_id))
        )
    ).scalar_one()
    assert payment.status == PaymentStatus.FAILED.value
    assert payment.processed_at is not None

    webhook = webhook_receiver.received[0]
    assert webhook["payment_id"] == payment_id
    assert webhook["status"] == PaymentStatus.FAILED.value
    assert webhook["amount"] == "17.00"
    assert webhook["currency"] == "USD"
