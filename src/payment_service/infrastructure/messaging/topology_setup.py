from __future__ import annotations

from payment_service.infrastructure.messaging.topology import (
    DLX_EXCHANGE,
    PAYMENTS_DEAD_ROUTING_KEY,
    PAYMENTS_DLQ,
    PAYMENTS_EXCHANGE,
    PAYMENTS_RETRY_QUEUE,
    PAYMENTS_RETRY_ROUTING_KEY,
    RETRY_EXCHANGE,
)
from payment_service.infrastructure.messaging.topology_broker import TopologyBroker


async def declare_topology(broker: TopologyBroker) -> None:
    await broker.declare_exchange(PAYMENTS_EXCHANGE)
    retry_exchange = await broker.declare_exchange(RETRY_EXCHANGE)
    dlx_exchange = await broker.declare_exchange(DLX_EXCHANGE)

    retry_queue = await broker.declare_queue(PAYMENTS_RETRY_QUEUE)
    await retry_queue.bind(retry_exchange, routing_key=PAYMENTS_RETRY_ROUTING_KEY)

    dead_letter_queue = await broker.declare_queue(PAYMENTS_DLQ)
    await dead_letter_queue.bind(dlx_exchange, routing_key=PAYMENTS_DEAD_ROUTING_KEY)
