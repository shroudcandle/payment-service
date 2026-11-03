from __future__ import annotations

from decimal import Decimal

from payment_service.domain.payment import Currency
from payment_service.domain.payment.events import PaymentCreatedDomainEvent
from tests.helpers.payments import make_payment


def test_create_records_correlation_id_in_event() -> None:
    payment = make_payment(
        amount=Decimal("10.00"),
        currency=Currency.EUR,
        description="Order",
        metadata={},
        idempotency_key="key",
        correlation_id="trace-1",
    )

    event = payment.events.peek()[0]
    assert isinstance(event, PaymentCreatedDomainEvent)
    assert event.correlation_id == "trace-1"
    assert event.to_primitives()["correlation_id"] == "trace-1"


def test_create_allows_missing_correlation_id() -> None:
    payment = make_payment(
        amount=Decimal("10.00"),
        currency=Currency.EUR,
        description="Order",
        metadata={},
        idempotency_key="key",
    )

    event = payment.events.peek()[0]
    assert isinstance(event, PaymentCreatedDomainEvent)
    assert event.correlation_id is None
