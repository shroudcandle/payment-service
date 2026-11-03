from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from payment_service.domain.payment import (
    Currency,
    IdempotencyKey,
    Money,
    Payment,
    PaymentStatus,
    WebhookUrl,
)
from payment_service.domain.payment.exceptions import InvalidStateTransitionError


class PaymentLifecycleMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.payment: Payment = Payment.create(
            money=Money(Decimal("99.99"), Currency.USD),
            description="stateful order",
            metadata={"source": "hypothesis"},
            idempotency_key=IdempotencyKey("stateful-key"),
            webhook_url=WebhookUrl("https://example.com/hook"),
        )

    @rule(at=st.datetimes(timezones=st.just(UTC)))
    @precondition(lambda self: not self.payment.is_processed)
    def complete_success(self, at: datetime) -> None:
        self.payment.complete_success(at)
        assert self.payment.status is PaymentStatus.SUCCEEDED

    @rule(at=st.datetimes(timezones=st.just(UTC)))
    @precondition(lambda self: not self.payment.is_processed)
    def complete_failure(self, at: datetime) -> None:
        self.payment.complete_failure(at)
        assert self.payment.status is PaymentStatus.FAILED

    @rule()
    @precondition(lambda self: self.payment.is_processed)
    def reject_second_terminal_transition(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            self.payment.complete_success(datetime.now(UTC))
        with pytest.raises(InvalidStateTransitionError):
            self.payment.complete_failure(datetime.now(UTC))

    @rule()
    def matches_original_request(self) -> None:
        assert self.payment.matches_request(
            money=Money(Decimal("99.99"), Currency.USD),
            description="stateful order",
            metadata={"source": "hypothesis"},
            webhook_url=WebhookUrl("https://example.com/hook"),
        )

    @invariant()
    def terminal_state_is_consistent(self) -> None:
        if self.payment.status is PaymentStatus.PENDING:
            assert not self.payment.is_processed
            assert self.payment.processed_at is None
        else:
            assert self.payment.is_processed
            assert self.payment.processed_at is not None
            assert self.payment.status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED)


TestPaymentLifecycle = PaymentLifecycleMachine.TestCase
TestPaymentLifecycle.settings = settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
