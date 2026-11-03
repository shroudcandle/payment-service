from __future__ import annotations

from payment_service.application.ports import EventPublisherPort
from payment_service.domain.outbox import OutboxEvent


class DiscardingEventPublisher(EventPublisherPort):
    async def publish(self, event: OutboxEvent) -> None:
        _ = event
