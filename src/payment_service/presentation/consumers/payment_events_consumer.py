from __future__ import annotations

import logging
from typing import Any

from dishka_faststream import FromDishka
from faststream.rabbit import RabbitBroker, RabbitMessage
from pydantic import ValidationError

from payment_service.application.commands import ProcessPaymentCommand, ProcessPaymentHandler
from payment_service.application.exceptions import PaymentNotFoundError, WebhookDeliveryError
from payment_service.config import WorkerSettings
from payment_service.domain.outbox import decide_retry
from payment_service.infrastructure.messaging import (
    DLX_EXCHANGE,
    PAYMENTS_DEAD_ROUTING_KEY,
    PAYMENTS_EXCHANGE,
    PAYMENTS_NEW_QUEUE,
    PAYMENTS_RETRY_ROUTING_KEY,
    RETRY_EXCHANGE,
)
from payment_service.presentation.consumers.payment_created_message import PaymentCreatedMessage

logger = logging.getLogger(__name__)


def register_payment_consumer(broker: RabbitBroker) -> None:
    @broker.subscriber(PAYMENTS_NEW_QUEUE, PAYMENTS_EXCHANGE)
    async def handle_payment_created(
        body: dict[str, Any],
        message: RabbitMessage,
        handler: FromDishka[ProcessPaymentHandler],
        settings: FromDishka[WorkerSettings],
    ) -> None:
        attempt = _read_attempt(message)
        try:
            payload = PaymentCreatedMessage.model_validate(body)
        except ValidationError as exc:
            correlation_id = _read_raw_correlation_id(message, body)
            logger.error(
                "Invalid payment.created payload: %s",
                exc,
                extra={"correlation_id": correlation_id},
            )
            await _publish_to_dlq(
                broker,
                body,
                reason="invalid payload",
                correlation_id=correlation_id,
            )
            return

        correlation_id = _read_correlation_id(message, payload)
        try:
            await handler.handle(
                ProcessPaymentCommand(
                    payment_id=payload.payment_id,
                    correlation_id=correlation_id,
                )
            )
        except PaymentNotFoundError:
            logger.warning(
                "Payment %s not found; routing message to DLQ",
                payload.payment_id,
                extra={"correlation_id": correlation_id},
            )
            await _publish_to_dlq(
                broker,
                body,
                reason="payment not found",
                correlation_id=correlation_id,
            )
        except WebhookDeliveryError as exc:
            await _schedule_retry(
                broker,
                body,
                attempt,
                str(exc),
                settings,
                correlation_id,
            )


def _read_attempt(message: RabbitMessage) -> int:
    raw = message.headers.get("x-retry-count", 0)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


async def _schedule_retry(
    broker: RabbitBroker,
    body: dict[str, Any],
    attempt: int,
    reason: str,
    settings: WorkerSettings,
    correlation_id: str | None,
) -> None:
    decision = decide_retry(
        attempt,
        settings.max_delivery_attempts,
        settings.retry_base,
        settings.retry_cap,
    )
    if not decision.should_retry:
        logger.error(
            "Webhook delivery exhausted %s attempts: %s",
            attempt,
            reason,
            extra={"correlation_id": correlation_id},
        )
        await _publish_to_dlq(
            broker,
            body,
            reason=reason,
            correlation_id=correlation_id,
        )
        return

    logger.warning(
        "Scheduling retry %s/%s in %sms: %s",
        decision.next_attempt,
        settings.max_delivery_attempts,
        decision.delay_ms,
        reason,
        extra={"correlation_id": correlation_id},
    )
    headers: dict[str, Any] = {"x-retry-count": decision.next_attempt}
    if correlation_id is not None:
        headers["x-correlation-id"] = correlation_id
    await broker.publish(
        body,
        exchange=RETRY_EXCHANGE,
        routing_key=PAYMENTS_RETRY_ROUTING_KEY,
        headers=headers,
        expiration=decision.delay_seconds,
    )


def _read_correlation_id(
    message: RabbitMessage,
    payload: PaymentCreatedMessage,
) -> str | None:
    raw = message.headers.get("x-correlation-id")
    if isinstance(raw, str) and raw:
        return raw
    return payload.correlation_id or None


def _read_raw_correlation_id(message: RabbitMessage, body: dict[str, Any]) -> str | None:
    raw = message.headers.get("x-correlation-id")
    if isinstance(raw, str) and raw:
        return raw
    candidate = body.get("correlation_id")
    return candidate if isinstance(candidate, str) and candidate else None


async def _publish_to_dlq(
    broker: RabbitBroker,
    body: dict[str, Any],
    reason: str,
    correlation_id: str | None,
) -> None:
    headers: dict[str, Any] = {"x-failure-reason": reason}
    if correlation_id is not None:
        headers["x-correlation-id"] = correlation_id
    await broker.publish(
        body,
        exchange=DLX_EXCHANGE,
        routing_key=PAYMENTS_DEAD_ROUTING_KEY,
        headers=headers,
    )
