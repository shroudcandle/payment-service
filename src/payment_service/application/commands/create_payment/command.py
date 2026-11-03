from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from payment_service.application.base import Command
from payment_service.application.commands.create_payment.result import CreatePaymentResult
from payment_service.domain.payment import Currency


@dataclass(frozen=True, slots=True)
class CreatePaymentCommand(Command[CreatePaymentResult]):
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    idempotency_key: str
    webhook_url: str
    correlation_id: str | None = None
