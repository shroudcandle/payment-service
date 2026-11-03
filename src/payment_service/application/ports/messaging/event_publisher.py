from __future__ import annotations

from typing import Protocol

from payment_service.domain.outbox import OutboxEvent


class EventPublisherPort(Protocol):
    async def publish(self, event: OutboxEvent) -> None: ...
