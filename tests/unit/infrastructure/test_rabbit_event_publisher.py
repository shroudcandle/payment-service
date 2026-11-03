from __future__ import annotations

import pytest
from aio_pika.exceptions import AMQPError

from payment_service.application.exceptions import EventPublishError
from payment_service.infrastructure.messaging import PAYMENTS_EXCHANGE, RabbitEventPublisher
from tests.fakes.publisher_recording_broker import PublisherRecordingBroker
from tests.helpers.payments import make_outbox_event


async def test_publish_sends_event_with_metadata() -> None:
    broker = PublisherRecordingBroker()
    event = make_outbox_event()

    await RabbitEventPublisher(broker).publish(event)

    assert len(broker.calls) == 1
    message, kwargs = broker.calls[0]
    assert message == event.payload
    assert kwargs["exchange"] is PAYMENTS_EXCHANGE
    assert kwargs["routing_key"] == event.routing_key
    assert kwargs["message_id"] == str(event.id)
    assert kwargs["persist"] is True
    assert kwargs["headers"] == {"x-event-id": str(event.id), "x-event-type": event.event_type}


@pytest.mark.parametrize("error", [AMQPError("broker down"), OSError("connection reset")])
async def test_publish_wraps_broker_failures(error: Exception) -> None:
    event = make_outbox_event()

    with pytest.raises(EventPublishError) as exc_info:
        await RabbitEventPublisher(PublisherRecordingBroker(error)).publish(event)

    assert exc_info.value.event_id == event.id
