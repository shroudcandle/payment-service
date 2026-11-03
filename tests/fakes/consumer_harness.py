from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from faststream.rabbit import TestRabbitBroker

from payment_service.infrastructure.messaging.topology import (
    PAYMENT_CREATED_ROUTING_KEY,
    PAYMENTS_EXCHANGE,
)
from tests.fakes.collected_message import CollectedMessage


@dataclass
class ConsumerHarness:
    dead: list[CollectedMessage] = field(default_factory=list)
    retried: list[CollectedMessage] = field(default_factory=list)
    broker: TestRabbitBroker | None = None

    async def publish(self, body: dict[str, Any], *, headers: dict[str, Any] | None = None) -> None:
        assert self.broker is not None
        await self.broker.publish(
            body,
            exchange=PAYMENTS_EXCHANGE,
            routing_key=PAYMENT_CREATED_ROUTING_KEY,
            headers=headers,
        )
