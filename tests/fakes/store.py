from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from payment_service.application.views import PaymentDetailsView
from payment_service.domain.outbox import OutboxEvent
from payment_service.domain.payment import Payment


@dataclass
class InMemoryStore:
    payments: dict[uuid.UUID, Payment] = field(default_factory=dict)
    outbox: list[OutboxEvent] = field(default_factory=list)
    webhook_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def idempotency_index(self) -> dict[str, Payment]:
        return {payment.idempotency_key.value: payment for payment in self.payments.values()}

    def view(self, payment: Payment) -> PaymentDetailsView:
        return PaymentDetailsView(
            id=payment.id,
            amount=payment.money.amount,
            currency=payment.money.currency,
            description=payment.description,
            metadata=payment.metadata,
            status=payment.status,
            idempotency_key=payment.idempotency_key.value,
            webhook_url=payment.webhook_url.value,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )
