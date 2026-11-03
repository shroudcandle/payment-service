from __future__ import annotations

from payment_service.infrastructure.messaging import (
    DLX_EXCHANGE,
    PAYMENTS_DEAD_ROUTING_KEY,
    PAYMENTS_DLQ,
    PAYMENTS_EXCHANGE,
    PAYMENTS_RETRY_QUEUE,
    PAYMENTS_RETRY_ROUTING_KEY,
    RETRY_EXCHANGE,
    declare_topology,
)
from tests.fakes.topology_recording_broker import TopologyRecordingBroker


async def test_declare_topology_creates_exchanges_queues_and_bindings() -> None:
    broker = TopologyRecordingBroker()

    await declare_topology(broker)

    assert broker.exchanges == [PAYMENTS_EXCHANGE.name, RETRY_EXCHANGE.name, DLX_EXCHANGE.name]
    assert [queue.name for queue in broker.queues] == [PAYMENTS_RETRY_QUEUE.name, PAYMENTS_DLQ.name]
    retry_queue, dead_letter_queue = broker.queues
    assert retry_queue.bindings == [(RETRY_EXCHANGE.name, PAYMENTS_RETRY_ROUTING_KEY)]
    assert dead_letter_queue.bindings == [(DLX_EXCHANGE.name, PAYMENTS_DEAD_ROUTING_KEY)]
