from __future__ import annotations

from decimal import Decimal

from payment_service.application.commands.create_payment.command import CreatePaymentCommand
from payment_service.domain.payment import Currency


def make_create_payment_command(
    *,
    amount: Decimal = Decimal("100.00"),
    idempotency_key: str = "key-1",
    description: str = "Order #1",
    webhook_url: str = "https://example.com/hook",
) -> CreatePaymentCommand:
    return CreatePaymentCommand(
        amount=amount,
        currency=Currency.RUB,
        description=description,
        metadata={"order": 1},
        idempotency_key=idempotency_key,
        webhook_url=webhook_url,
    )
