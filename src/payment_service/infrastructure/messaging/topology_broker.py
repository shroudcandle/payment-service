from __future__ import annotations

from typing import Protocol

from faststream.rabbit import RabbitExchange, RabbitQueue

from payment_service.infrastructure.messaging.topology_queue import TopologyQueue


class TopologyBroker(Protocol):
    async def declare_exchange(self, exchange: RabbitExchange) -> object: ...

    async def declare_queue(self, queue: RabbitQueue) -> TopologyQueue: ...
