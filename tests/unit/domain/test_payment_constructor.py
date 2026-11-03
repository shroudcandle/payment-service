from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from payment_service.domain.payment import (
    Currency,
    IdempotencyKey,
    Money,
    Payment,
    PaymentStatus,
    WebhookUrl,
)
from tests.helpers.payments import make_payment


def test_create_stores_all_fields_and_generates_identity() -> None:
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    payment = make_payment(now=now)

    assert isinstance(payment.id, uuid.UUID)
    assert payment.money == Money(Decimal("100.00"), Currency.RUB)
    assert payment.description == "Order #1"
    assert payment.metadata == {"order": 1}
    assert payment.idempotency_key == IdempotencyKey("key-1")
    assert payment.webhook_url == WebhookUrl("https://example.com/hook")
    assert payment.created_at == now
    assert payment.created_at.tzinfo is UTC
    assert payment.processed_at is None


def test_constructor_preserves_processed_at() -> None:
    processed_at = datetime(2026, 2, 3, 4, 5, 6, tzinfo=UTC)
    payment = Payment(
        payment_id=uuid.uuid4(),
        money=Money(Decimal("1.00"), Currency.EUR),
        description="Stored",
        metadata={"k": "v"},
        idempotency_key=IdempotencyKey("stored-key"),
        webhook_url=WebhookUrl("https://example.com/hook"),
        status=PaymentStatus.SUCCEEDED,
        created_at=processed_at,
        processed_at=processed_at,
    )

    assert payment.id is not None
    assert payment.idempotency_key == IdempotencyKey("stored-key")
    assert payment.processed_at == processed_at


def test_create_uses_utc_now_when_not_provided() -> None:
    payment = make_payment()

    assert payment.created_at.tzinfo is UTC
