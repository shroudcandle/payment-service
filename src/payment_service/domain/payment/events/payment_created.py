from __future__ import annotations

import uuid
from dataclasses import dataclass

from payment_service.domain.base import DomainEvent


@dataclass(frozen=True, slots=True)
class PaymentCreatedDomainEvent(DomainEvent):
    payment_id: uuid.UUID
    correlation_id: str | None = None

    @classmethod
    def event_name(cls) -> str:
        return "payment.created"
