from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from payment_service.domain.base import AggregateRoot
from payment_service.domain.payment.events import PaymentCreatedDomainEvent
from payment_service.domain.payment.exceptions import (
    InvalidDescriptionError,
    InvalidStateTransitionError,
)
from payment_service.domain.payment.value_objects import (
    IdempotencyKey,
    Money,
    PaymentStatus,
    WebhookUrl,
)


class Payment(AggregateRoot[uuid.UUID]):
    __slots__ = (
        "created_at",
        "description",
        "idempotency_key",
        "metadata",
        "money",
        "processed_at",
        "status",
        "webhook_url",
    )

    def __init__(
        self,
        payment_id: uuid.UUID,
        money: Money,
        description: str,
        metadata: dict[str, Any],
        idempotency_key: IdempotencyKey,
        webhook_url: WebhookUrl,
        status: PaymentStatus,
        created_at: datetime,
        processed_at: datetime | None = None,
    ) -> None:
        super().__init__(payment_id)
        if not description.strip():
            raise InvalidDescriptionError("description must not be empty")
        self.money = money
        self.description = description
        self.metadata = metadata
        self.idempotency_key = idempotency_key
        self.webhook_url = webhook_url
        self.status = status
        self.created_at = created_at
        self.processed_at = processed_at

    @classmethod
    def create(
        cls,
        *,
        money: Money,
        description: str,
        metadata: dict[str, Any],
        idempotency_key: IdempotencyKey,
        webhook_url: WebhookUrl,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Payment:
        payment = cls(
            payment_id=uuid.uuid4(),
            money=money,
            description=description,
            metadata=metadata,
            idempotency_key=idempotency_key,
            webhook_url=webhook_url,
            status=PaymentStatus.PENDING,
            created_at=now or datetime.now(UTC),
        )
        payment.events.record(
            PaymentCreatedDomainEvent(
                payment_id=payment.id,
                correlation_id=correlation_id,
            )
        )
        return payment

    @property
    def is_processed(self) -> bool:
        return self.status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED)

    def complete_success(self, at: datetime) -> None:
        self._ensure_pending()
        self.status = PaymentStatus.SUCCEEDED
        self.processed_at = at

    def complete_failure(self, at: datetime) -> None:
        self._ensure_pending()
        self.status = PaymentStatus.FAILED
        self.processed_at = at

    def matches_request(
        self,
        *,
        money: Money,
        description: str,
        metadata: dict[str, Any],
        webhook_url: WebhookUrl,
    ) -> bool:
        return (
            self.money == money
            and self.description == description
            and self.metadata == metadata
            and self.webhook_url == webhook_url
        )

    def _ensure_pending(self) -> None:
        if self.status != PaymentStatus.PENDING:
            raise InvalidStateTransitionError(
                f"cannot transition payment {self.id} from {self.status.value}"
            )
