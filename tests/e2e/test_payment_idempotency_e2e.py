from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.infrastructure.persistence.tables import OutboxTable, PaymentTable
from tests.e2e.constants import API_KEY
from tests.e2e.webhook_receiver import WebhookReceiver
from tests.helpers.network import wait_for


async def test_duplicate_request_reuses_payment_without_extra_webhook(
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
        "description": "Idempotent order",
        "metadata": {"order": "e2e"},
        "webhook_url": webhook_receiver.url,
    }

    async with httpx.AsyncClient(base_url=api_server, timeout=10.0) as client:
        created = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert created.status_code == 202
        created_body = created.json()
        payment_id = created_body["payment_id"]

        async def webhook_delivered() -> bool:
            return len(webhook_receiver.received) == 1

        await wait_for(webhook_delivered, timeout=30.0, message="webhook was not delivered")

        duplicate = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert duplicate.status_code == 202
        assert duplicate.json()["payment_id"] == payment_id
        assert duplicate.json()["created_at"] == created_body["created_at"]

    payments_count = await db_session.scalar(select(func.count()).select_from(PaymentTable))
    outbox_count = await db_session.scalar(select(func.count()).select_from(OutboxTable))
    assert payments_count == 1
    assert outbox_count == 1
    assert len(webhook_receiver.received) == 1
    assert webhook_receiver.received[0]["payment_id"] == payment_id


async def test_conflicting_payload_with_same_key_is_rejected(
    api_server: str,
    db_session: AsyncSession,
    webhook_receiver: WebhookReceiver,
) -> None:
    idempotency_key = f"e2e-{uuid.uuid4()}"
    headers = {"X-API-Key": API_KEY, "Idempotency-Key": idempotency_key}
    payload: dict[str, Any] = {
        "amount": "42.00",
        "currency": "RUB",
        "description": "Original order",
        "metadata": {"order": "e2e"},
        "webhook_url": webhook_receiver.url,
    }
    conflicting = {**payload, "amount": "999.00"}

    async with httpx.AsyncClient(base_url=api_server, timeout=10.0) as client:
        created = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert created.status_code == 202
        payment_id = created.json()["payment_id"]

        response = await client.post("/api/v1/payments", json=conflicting, headers=headers)
        assert response.status_code == 409

    db_session.expire_all()
    payment = (
        await db_session.execute(
            select(PaymentTable).where(PaymentTable.id == uuid.UUID(payment_id))
        )
    ).scalar_one()
    payments_count = await db_session.scalar(select(func.count()).select_from(PaymentTable))
    assert payments_count == 1
    assert payment.amount == Decimal("42.00")
    assert payment.description == "Original order"
