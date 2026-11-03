from __future__ import annotations

from typing import Any

from aio_pika.exceptions import AMQPError
from faststream.rabbit import RabbitBroker

from payment_service.application.exceptions import EventPublishError
from payment_service.application.ports import EventPublisherPort
from payment_service.domain.outbox import OutboxEvent
from payment_service.infrastructure.messaging.topology import PAYMENTS_EXCHANGE


class RabbitEventPublisher(EventPublisherPort):
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish(self, event: OutboxEvent) -> None:
        try:
            await self._broker.publish(
                event.payload,
                exchange=PAYMENTS_EXCHANGE,
                routing_key=event.routing_key,
                headers=_headers(event),
                message_id=str(event.id),
                persist=True,
            )
        except (AMQPError, OSError) as exc:
            raise EventPublishError(event.id, str(exc)) from exc


def _headers(event: OutboxEvent) -> dict[str, Any]:
    headers = {"x-event-id": str(event.id), "x-event-type": event.event_type}
    correlation_id = event.payload.get("correlation_id")
    if isinstance(correlation_id, str) and correlation_id:
        headers["x-correlation-id"] = correlation_id
    return headers
