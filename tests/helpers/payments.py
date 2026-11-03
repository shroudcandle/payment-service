from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from payment_service.application.commands.create_payment.command import CreatePaymentCommand
from payment_service.domain.outbox import OutboxEvent
from payment_service.domain.payment import (
    Currency,
    IdempotencyKey,
    Money,
    Payment,
    WebhookUrl,
)

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def make_payment(
    *,
    amount: Decimal = Decimal("100.00"),
    currency: Currency = Currency.RUB,
    description: str = "Order #1",
    metadata: dict[str, Any] | None = None,
    idempotency_key: str = "key-1",
    webhook_url: str = "https://example.com/hook",
    correlation_id: str | None = None,
    now: datetime | None = None,
) -> Payment:
    return Payment.create(
        money=Money(amount, currency),
        description=description,
        metadata=metadata if metadata is not None else {"order": 1},
        idempotency_key=IdempotencyKey(idempotency_key),
        webhook_url=WebhookUrl(webhook_url),
        correlation_id=correlation_id,
        now=now,
    )


def make_conflicting_payment(command: CreatePaymentCommand) -> Payment:
    return make_payment(
        amount=Decimal("999.00"),
        currency=command.currency,
        description=command.description,
        metadata=command.metadata,
        idempotency_key=command.idempotency_key,
        webhook_url=command.webhook_url,
    )


def make_outbox_event(
    *,
    payload: dict[str, Any] | None = None,
    created_at: datetime = NOW,
) -> OutboxEvent:
    event_id = uuid.uuid4()
    return OutboxEvent.from_domain_event(
        event_id=event_id,
        event_type="payment.created",
        routing_key="payment.created",
        payload=payload if payload is not None else {"payment_id": str(uuid.uuid4())},
        created_at=created_at,
    )
