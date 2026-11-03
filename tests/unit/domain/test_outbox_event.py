from __future__ import annotations

import uuid
from datetime import UTC, datetime

from payment_service.domain.outbox import OutboxEvent, OutboxStatus

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_from_domain_event_builds_pending_event() -> None:
    event_id = uuid.uuid4()

    event = OutboxEvent.from_domain_event(
        event_id=event_id,
        event_type="payment.created",
        routing_key="payment.created",
        payload={"event_id": str(event_id)},
        created_at=NOW,
    )

    assert event.id == event_id
    assert event.event_type == "payment.created"
    assert event.routing_key == "payment.created"
    assert event.payload == {"event_id": str(event_id)}
    assert event.status is OutboxStatus.PENDING
    assert event.retry_count == 0
    assert event.created_at == NOW
    assert event.error_log is None
    assert event.processed_at is None
    assert event.next_attempt_at is None
