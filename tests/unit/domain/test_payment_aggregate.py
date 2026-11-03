from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from payment_service.domain.payment import (
    Currency,
    IdempotencyKey,
    Money,
    Payment,
    PaymentStatus,
    WebhookUrl,
)
from payment_service.domain.payment.events.payment_created import PaymentCreatedDomainEvent
from payment_service.domain.payment.exceptions import (
    InvalidDescriptionError,
    InvalidStateTransitionError,
)
from tests.helpers.payments import make_payment


def test_create_returns_pending_payment_and_records_event() -> None:
    payment = make_payment()

    assert payment.status is PaymentStatus.PENDING
    assert payment.processed_at is None
    assert not payment.is_processed
    events = payment.events.peek()
    assert len(events) == 1
    assert isinstance(events[0], PaymentCreatedDomainEvent)
    assert events[0].payment_id == payment.id
    assert events[0].routing_key() == "payment.created"


def test_complete_success_sets_terminal_state() -> None:
    payment = make_payment()
    processed_at = datetime.now(UTC)

    payment.complete_success(processed_at)

    assert payment.status is PaymentStatus.SUCCEEDED
    assert payment.processed_at == processed_at
    assert payment.is_processed


def test_complete_failure_sets_terminal_state() -> None:
    payment = make_payment()

    payment.complete_failure(datetime.now(UTC))

    assert payment.status is PaymentStatus.FAILED
    assert payment.is_processed


def test_terminal_state_cannot_transition_again() -> None:
    payment = make_payment()
    payment.complete_success(datetime.now(UTC))

    with pytest.raises(InvalidStateTransitionError):
        payment.complete_failure(datetime.now(UTC))


def test_matches_request_compares_payload() -> None:
    payment = make_payment()

    assert payment.matches_request(
        money=Money(Decimal("100.00"), Currency.RUB),
        description="Order #1",
        metadata={"order": 1},
        webhook_url=WebhookUrl("https://example.com/hook"),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("money", Money(Decimal("100.50"), Currency.RUB)),
        ("money", Money(Decimal("100.00"), Currency.USD)),
        ("description", "Other"),
        ("metadata", {"order": 2}),
        ("webhook_url", WebhookUrl("https://example.com/other")),
    ],
)
def test_matches_request_rejects_any_payload_difference(field: str, value: Any) -> None:
    payment = make_payment()
    request: dict[str, Any] = {
        "money": Money(Decimal("100.00"), Currency.RUB),
        "description": "Order #1",
        "metadata": {"order": 1},
        "webhook_url": WebhookUrl("https://example.com/hook"),
        field: value,
    }

    assert not payment.matches_request(**request)


def test_clear_events_discards_recorded_events() -> None:
    payment = make_payment()

    payment.events.clear()

    assert payment.events.peek() == ()


@pytest.mark.parametrize("description", ["", "   ", "\t\n"])
def test_create_rejects_blank_description(description: str) -> None:
    with pytest.raises(InvalidDescriptionError):
        Payment.create(
            money=Money(Decimal("100.00"), Currency.RUB),
            description=description,
            metadata={},
            idempotency_key=IdempotencyKey("key-1"),
            webhook_url=WebhookUrl("https://example.com/hook"),
        )
