from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from payment_service.domain.payment.events import PaymentCreatedDomainEvent
from tests.fakes.sample_event import SampleEvent


def test_event_name_defaults_to_class_name() -> None:
    assert SampleEvent.event_name() == "SampleEvent"
    assert SampleEvent.routing_key() == "SampleEvent"


def test_payment_created_event_has_explicit_name_and_routing_key() -> None:
    assert PaymentCreatedDomainEvent.event_name() == "payment.created"
    assert PaymentCreatedDomainEvent.routing_key() == "payment.created"


def test_to_primitives_serialises_uuid_and_datetime_fields() -> None:
    payment_id = uuid.uuid4()
    happened_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    event = SampleEvent(payment_id=payment_id, happened_at=happened_at)

    primitives = event.to_primitives()

    assert primitives["event_id"] == str(event.event_id)
    assert primitives["event_name"] == "SampleEvent"
    assert primitives["occurred_on"] == event.occurred_on.isoformat()
    assert event.occurred_on.tzinfo is UTC
    assert primitives["payment_id"] == str(payment_id)
    assert primitives["happened_at"] == happened_at.isoformat()
    assert primitives["note"] == "note"


def test_payment_created_event_serialises_payment_id() -> None:
    payment_id = uuid.uuid4()

    primitives = PaymentCreatedDomainEvent(payment_id=payment_id).to_primitives()

    assert primitives["event_name"] == "payment.created"
    assert primitives["payment_id"] == str(payment_id)


def test_events_are_immutable() -> None:
    event = PaymentCreatedDomainEvent(payment_id=uuid.uuid4())

    with pytest.raises(FrozenInstanceError):
        event.payment_id = uuid.uuid4()
