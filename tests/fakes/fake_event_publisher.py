from __future__ import annotations

from dataclasses import dataclass, field

from payment_service.application.exceptions import EventPublishError
from payment_service.application.ports import EventPublisherPort
from payment_service.domain.outbox import OutboxEvent


@dataclass
class FakeEventPublisher(EventPublisherPort):
    error: EventPublishError | None = None
    published: list[OutboxEvent] = field(default_factory=list)

    async def publish(self, event: OutboxEvent) -> None:
        if self.error is not None:
            raise self.error
        self.published.append(event)
