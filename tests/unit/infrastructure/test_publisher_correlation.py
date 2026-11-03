from __future__ import annotations

from payment_service.infrastructure.messaging import RabbitEventPublisher
from tests.fakes.publisher_recording_broker import PublisherRecordingBroker
from tests.helpers.payments import make_outbox_event


async def test_publish_propagates_correlation_id_header() -> None:
    broker = PublisherRecordingBroker()
    event = make_outbox_event(payload={"payment_id": "p-1", "correlation_id": "trace-1"})

    await RabbitEventPublisher(broker).publish(event)

    _, kwargs = broker.calls[0]
    assert kwargs["headers"]["x-correlation-id"] == "trace-1"


async def test_publish_skips_blank_correlation_id() -> None:
    broker = PublisherRecordingBroker()
    event = make_outbox_event(payload={"payment_id": "p-1", "correlation_id": ""})

    await RabbitEventPublisher(broker).publish(event)

    _, kwargs = broker.calls[0]
    assert "x-correlation-id" not in kwargs["headers"]
