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


async def test_exhausted_webhook_retries_reach_dead_letter_queue(
    infrastructure: str,
    fast_webhook_retry: None,
    api_server: str,
    worker: None,
    dead_letters: list[dict[str, Any]],
    webhook_receiver: WebhookReceiver,
    db_session: AsyncSession,
) -> None:
    _ = infrastructure, fast_webhook_retry, worker
    webhook_receiver.failures_remaining = 10
    idempotency_key = f"e2e-{uuid.uuid4()}"
    headers = {"X-API-Key": API_KEY, "Idempotency-Key": idempotency_key}
    payload: dict[str, Any] = {
        "amount": "23.00",
        "currency": "EUR",
        "description": "Undeliverable webhook",
        "metadata": {"order": "dlq"},
        "webhook_url": webhook_receiver.url,
    }

    async with httpx.AsyncClient(base_url=api_server, timeout=10.0) as client:
        created = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert created.status_code == 202
        payment_id = created.json()["payment_id"]

    async def dead_letter_received() -> bool:
        return len(dead_letters) == 1

    await wait_for(
        dead_letter_received,
        timeout=40.0,
        message="message did not reach payments.dlq",
    )

    assert webhook_receiver.received == []
    assert webhook_receiver.attempts >= 2
    message = dead_letters[0]
    assert message["body"]["payment_id"] == payment_id
    assert "receiver responded with 500" in message["headers"]["x-failure-reason"]

    db_session.expire_all()
    payment = (
        await db_session.execute(
            select(PaymentTable).where(PaymentTable.id == uuid.UUID(payment_id))
        )
    ).scalar_one()
    assert payment.status == PaymentStatus.SUCCEEDED.value
