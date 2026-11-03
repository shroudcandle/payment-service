from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from payment_service.application.views import PaymentDetailsView
from payment_service.domain.payment import (
    Currency,
    IdempotencyKey,
    Money,
    Payment,
    PaymentStatus,
    WebhookUrl,
)
from payment_service.infrastructure.persistence.tables import PaymentTable


class PaymentMapper:
    @staticmethod
    def to_domain(row: PaymentTable) -> Payment:
        return Payment(
            payment_id=row.id,
            money=Money(row.amount, Currency(row.currency)),
            description=row.description,
            metadata=row.metadata_json,
            idempotency_key=IdempotencyKey(row.idempotency_key),
            webhook_url=WebhookUrl(row.webhook_url),
            status=PaymentStatus(row.status),
            created_at=row.created_at,
            processed_at=row.processed_at,
        )

    @staticmethod
    def to_view(row: PaymentTable) -> PaymentDetailsView:
        return PaymentDetailsView(
            id=row.id,
            amount=row.amount,
            currency=Currency(row.currency),
            description=row.description,
            metadata=row.metadata_json,
            status=PaymentStatus(row.status),
            idempotency_key=row.idempotency_key,
            webhook_url=_without_credentials(row.webhook_url),
            created_at=row.created_at,
            processed_at=row.processed_at,
        )

    @staticmethod
    def to_table(payment: Payment) -> PaymentTable:
        return PaymentTable(
            id=payment.id,
            amount=payment.money.amount,
            currency=payment.money.currency.value,
            description=payment.description,
            metadata_json=payment.metadata,
            status=payment.status.value,
            idempotency_key=payment.idempotency_key.value,
            webhook_url=payment.webhook_url.value,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )

    @staticmethod
    def apply(payment: Payment, row: PaymentTable) -> None:
        row.amount = payment.money.amount
        row.currency = payment.money.currency.value
        row.description = payment.description
        row.metadata_json = payment.metadata
        row.status = payment.status.value
        row.idempotency_key = payment.idempotency_key.value
        row.webhook_url = payment.webhook_url.value
        row.created_at = payment.created_at
        row.processed_at = payment.processed_at


def _without_credentials(url: str) -> str:
    parsed = urlparse(url)
    if parsed.username is None and parsed.password is None:
        return url
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=host))
