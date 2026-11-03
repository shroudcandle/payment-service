from __future__ import annotations

import uuid

from payment_service.domain.outbox import OutboxStatus
from payment_service.domain.payment import Currency, PaymentStatus
from payment_service.domain.payment.events import PaymentCreatedDomainEvent
from payment_service.infrastructure.persistence.mappers import OutboxMapper, PaymentMapper
from payment_service.infrastructure.persistence.tables import OutboxTable
from tests.helpers.payments import NOW, make_payment
from tests.helpers.persistence import make_payment_table


def test_payment_mapper_round_trips_domain_payment() -> None:
    payment = make_payment(now=NOW)

    row = PaymentMapper.to_table(payment)
    restored = PaymentMapper.to_domain(row)

    assert row.id == payment.id
    assert row.currency == Currency.RUB.value
    assert row.status == PaymentStatus.PENDING.value
    assert restored.id == payment.id
    assert restored.money == payment.money
    assert restored.money.currency is Currency.RUB
    assert restored.status is PaymentStatus.PENDING


def test_payment_mapper_projects_view() -> None:
    row = make_payment_table(make_payment(now=NOW))

    view = PaymentMapper.to_view(row)

    assert view.id == row.id
    assert view.amount == row.amount
    assert view.currency is Currency.RUB
    assert view.status is PaymentStatus.PENDING


def test_payment_mapper_strips_credentials_from_view_url() -> None:
    row = make_payment_table(make_payment(now=NOW))
    row.webhook_url = "https://user:secret@example.com:8443/hook"

    view = PaymentMapper.to_view(row)

    assert view.webhook_url == "https://example.com:8443/hook"


def test_payment_mapper_strips_credentials_without_port() -> None:
    row = make_payment_table(make_payment(now=NOW))
    row.webhook_url = "https://user:secret@example.com/hook"

    view = PaymentMapper.to_view(row)

    assert view.webhook_url == "https://example.com/hook"


def test_payment_mapper_applies_mutable_state() -> None:
    payment = make_payment(now=NOW)
    row = PaymentMapper.to_table(payment)
    payment.complete_success(NOW)

    PaymentMapper.apply(payment, row)

    assert row.status == PaymentStatus.SUCCEEDED.value
    assert row.processed_at == NOW


def test_outbox_mapper_builds_row_from_domain_event() -> None:
    event = PaymentCreatedDomainEvent(payment_id=uuid.uuid4())

    row = OutboxMapper.to_table(event)

    assert row.id == event.event_id
    assert row.event_type == "payment.created"
    assert row.routing_key == "payment.created"
    assert row.status == OutboxStatus.PENDING.value
    assert row.retry_count == 0


def test_outbox_mapper_restores_domain_event() -> None:
    event_id = uuid.uuid4()
    row = OutboxTable(
        id=event_id,
        event_type="payment.created",
        routing_key="payment.created",
        payload={"event_id": str(event_id)},
        status=OutboxStatus.PUBLISHED.value,
        retry_count=2,
        error_log="boom",
        created_at=NOW,
        processed_at=NOW,
        next_attempt_at=None,
    )

    event = OutboxMapper.to_domain(row)

    assert event.id == event_id
    assert event.status is OutboxStatus.PUBLISHED
    assert event.retry_count == 2
    assert event.error_log == "boom"
    assert event.processed_at == NOW
