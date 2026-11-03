from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from payment_service.domain.outbox import OutboxStatus
from payment_service.domain.payment import Payment
from payment_service.infrastructure.persistence.mappers import PaymentMapper
from payment_service.infrastructure.persistence.tables import OutboxTable, PaymentTable
from tests.helpers.payments import NOW, make_payment


def make_payment_table(payment: Payment | None = None) -> PaymentTable:
    return PaymentMapper.to_table(payment or make_payment(now=NOW))


def make_outbox_table(
    *,
    status: OutboxStatus = OutboxStatus.PENDING,
    created_at: datetime = NOW,
    payload: dict[str, Any] | None = None,
) -> OutboxTable:
    event_id = uuid.uuid4()
    return OutboxTable(
        id=event_id,
        event_type="payment.created",
        routing_key="payment.created",
        payload=payload if payload is not None else {"event_id": str(event_id)},
        status=status.value,
        retry_count=0,
        error_log=None,
        created_at=created_at,
        processed_at=None,
        next_attempt_at=None,
    )
