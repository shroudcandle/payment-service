from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.domain.outbox import OutboxStatus
from payment_service.domain.payment import PaymentStatus
from payment_service.infrastructure.persistence.tables import OutboxTable, PaymentTable
from tests.e2e.constants import API_KEY, TERMINAL_STATUSES
from tests.e2e.webhook_receiver import WebhookReceiver
from tests.helpers.network import wait_for


async def test_payment_lifecycle_persists_state_and_notifies_receiver(
    api_server: str,
    worker: None,
    db_session: AsyncSession,
    webhook_receiver: WebhookReceiver,
) -> None:
    _ = worker
    idempotency_key = f"e2e-{uuid.uuid4()}"
    headers = {"X-API-Key": API_KEY, "Idempotency-Key": idempotency_key}
    payload: dict[str, Any] = {
        "amount": "42.00",
        "currency": "RUB",
        "description": "E2E order",
        "metadata": {"order": "e2e"},
        "webhook_url": webhook_receiver.url,
    }

    async with httpx.AsyncClient(base_url=api_server, timeout=10.0) as client:
        health = await client.get("/health", headers={"X-API-Key": API_KEY})
        assert health.json() == {
            "status": "ok",
            "postgres": "connected",
            "rabbitmq": "connected",
        }

        created = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert created.status_code == 202
        created_body = created.json()
        assert created_body["status"] == PaymentStatus.PENDING.value
        payment_id = created_body["payment_id"]

        async def payment_is_terminal() -> bool:
            response = await client.get(
                f"/api/v1/payments/{payment_id}",
                headers={"X-API-Key": API_KEY},
            )
            return response.json()["status"] in TERMINAL_STATUSES

        await wait_for(
            payment_is_terminal,
            timeout=30.0,
            message="payment was not processed to a terminal state",
        )
        details = await client.get(
            f"/api/v1/payments/{payment_id}",
            headers={"X-API-Key": API_KEY},
        )

    async def webhook_delivered() -> bool:
        return len(webhook_receiver.received) == 1

    await wait_for(webhook_delivered, timeout=15.0, message="webhook was not delivered")

    body = details.json()
    assert body["id"] == payment_id
    assert body["amount"] == "42.00"
    assert body["currency"] == "RUB"
    assert body["description"] == "E2E order"
    assert body["metadata"] == {"order": "e2e"}
    assert body["status"] == PaymentStatus.SUCCEEDED.value
    assert body["idempotency_key"] == idempotency_key
    assert body["webhook_url"] == webhook_receiver.url
    created_at = datetime.fromisoformat(body["created_at"])
    processed_at = datetime.fromisoformat(body["processed_at"])
    assert created_at <= processed_at

    payment = (
        await db_session.execute(
            select(PaymentTable).where(PaymentTable.id == uuid.UUID(payment_id))
        )
    ).scalar_one()
    assert payment.status == PaymentStatus.SUCCEEDED.value
    assert payment.amount == Decimal("42.00")
    assert payment.currency == "RUB"
    assert payment.idempotency_key == idempotency_key
    assert payment.processed_at is not None

    async def outbox_published() -> bool:
        db_session.expire_all()
        outbox = (await db_session.execute(select(OutboxTable))).scalar_one()
        return outbox.status == OutboxStatus.PUBLISHED.value

    await wait_for(outbox_published, timeout=15.0, message="outbox event was not published")
    outbox = (await db_session.execute(select(OutboxTable))).scalar_one()
    assert outbox.payload["payment_id"] == payment_id
    assert outbox.retry_count == 0
    assert outbox.error_log is None
    assert outbox.processed_at is not None

    webhook = webhook_receiver.received[0]
    assert webhook["event"] == "payment.updated"
    assert webhook["payment_id"] == payment_id
    assert webhook["status"] == PaymentStatus.SUCCEEDED.value
    assert webhook["amount"] == "42.00"
    assert webhook["currency"] == "RUB"
    assert webhook["metadata"] == {"order": "e2e"}
    assert datetime.fromisoformat(webhook["processed_at"]) == processed_at
