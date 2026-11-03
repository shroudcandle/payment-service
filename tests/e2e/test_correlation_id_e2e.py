from __future__ import annotations

import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.infrastructure.persistence.tables import OutboxTable
from tests.e2e.constants import API_KEY
from tests.e2e.webhook_receiver import WebhookReceiver
from tests.helpers.network import wait_for


async def test_request_id_reaches_outbox_worker_and_webhook(
    infrastructure: str,
    api_server: str,
    worker: None,
    db_session: AsyncSession,
    webhook_receiver: WebhookReceiver,
) -> None:
    _ = infrastructure, worker
    correlation_id = f"trace-{uuid.uuid4()}"
    headers = {
        "X-API-Key": API_KEY,
        "Idempotency-Key": f"e2e-{uuid.uuid4()}",
        "X-Request-ID": correlation_id,
    }
    payload: dict[str, Any] = {
        "amount": "31.00",
        "currency": "RUB",
        "description": "Correlated order",
        "metadata": {"order": "correlation"},
        "webhook_url": webhook_receiver.url,
    }

    async with httpx.AsyncClient(base_url=api_server, timeout=10.0) as client:
        created = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert created.status_code == 202
        assert created.headers["X-Request-ID"] == correlation_id
        payment_id = created.json()["payment_id"]

    async def webhook_delivered() -> bool:
        return len(webhook_receiver.received) == 1

    await wait_for(webhook_delivered, timeout=30.0, message="webhook was not delivered")

    webhook = webhook_receiver.received[0]
    assert webhook["correlation_id"] == correlation_id
    assert webhook_receiver.received_headers[0]["x-correlation-id"] == correlation_id

    outbox = (
        await db_session.execute(
            select(OutboxTable).where(OutboxTable.payload["payment_id"].astext == payment_id)
        )
    ).scalar_one()
    assert outbox.payload["correlation_id"] == correlation_id
