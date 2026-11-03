from __future__ import annotations

import uuid


class ApplicationError(Exception):
    pass


class IdempotencyConflictError(ApplicationError):
    def __init__(self, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(
            f"Idempotency key {idempotency_key!r} is already used with different payload"
        )


class DuplicateIdempotencyKeyError(ApplicationError):
    def __init__(self, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(f"Idempotency key {idempotency_key!r} already exists")


class PaymentNotFoundError(ApplicationError):
    def __init__(self, payment_id: uuid.UUID) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id} not found")


class WebhookDeliveryError(ApplicationError):
    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Webhook delivery to {url} failed: {reason}")


class EventPublishError(ApplicationError):
    def __init__(self, event_id: uuid.UUID, reason: str) -> None:
        self.event_id = event_id
        self.reason = reason
        super().__init__(f"Failed to publish outbox event {event_id}: {reason}")


class NonRetryableWebhookError(ApplicationError):
    def __init__(self, url: str, status_code: int) -> None:
        self.url = url
        self.status_code = status_code
        super().__init__(f"Webhook {url} returned non-retryable status {status_code}")
