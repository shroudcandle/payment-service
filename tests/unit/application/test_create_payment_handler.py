from __future__ import annotations

from decimal import Decimal

import pytest

from payment_service.application.commands.create_payment.handler import CreatePaymentHandler
from payment_service.application.exceptions import (
    DuplicateIdempotencyKeyError,
    IdempotencyConflictError,
)
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.domain.payment import PaymentStatus
from tests.factories import make_create_payment_command
from tests.fakes.store import InMemoryStore
from tests.helpers.payments import make_conflicting_payment
from tests.helpers.uow import make_racing_factory


async def test_creates_payment_and_outbox_event(
    store: InMemoryStore, uow_factory: UnitOfWorkFactoryPort
) -> None:
    handler = CreatePaymentHandler(uow_factory)

    result = await handler.handle(make_create_payment_command())

    assert result.status is PaymentStatus.PENDING
    assert store.payments[result.payment_id].money.amount == Decimal("100.00")
    assert len(store.outbox) == 1
    assert store.outbox[0].event_type == "payment.created"
    assert store.outbox[0].routing_key == "payment.created"
    assert store.outbox[0].payload["payment_id"] == str(result.payment_id)


async def test_same_idempotency_key_and_payload_returns_existing_payment(
    store: InMemoryStore, uow_factory: UnitOfWorkFactoryPort
) -> None:
    handler = CreatePaymentHandler(uow_factory)

    first = await handler.handle(make_create_payment_command())
    second = await handler.handle(make_create_payment_command())

    assert first.payment_id == second.payment_id
    assert len(store.payments) == 1
    assert len(store.outbox) == 1


async def test_same_idempotency_key_with_different_payload_conflicts(
    store: InMemoryStore, uow_factory: UnitOfWorkFactoryPort
) -> None:
    handler = CreatePaymentHandler(uow_factory)
    await handler.handle(make_create_payment_command())

    with pytest.raises(IdempotencyConflictError):
        await handler.handle(make_create_payment_command(amount=Decimal("100.50")))


async def test_commit_race_returns_payment_created_by_concurrent_request() -> None:
    store = InMemoryStore()
    factory, created = make_racing_factory(store)

    result = await CreatePaymentHandler(factory).handle(make_create_payment_command())

    assert result.status is PaymentStatus.PENDING
    assert result.payment_id in store.payments
    assert created[0].rolled_back


async def test_commit_race_with_different_payload_conflicts() -> None:
    race_store = InMemoryStore()
    conflicting_store = InMemoryStore()
    command = make_create_payment_command()
    conflicting = make_conflicting_payment(command)
    conflicting_store.payments[conflicting.id] = conflicting
    factory, _ = make_racing_factory(race_store, conflicting_store)

    with pytest.raises(IdempotencyConflictError):
        await CreatePaymentHandler(factory).handle(command)


async def test_commit_race_without_visible_payment_reraises_duplicate() -> None:
    first_store = InMemoryStore()
    second_store = InMemoryStore()
    factory, _ = make_racing_factory(first_store, second_store)

    with pytest.raises(DuplicateIdempotencyKeyError):
        await CreatePaymentHandler(factory).handle(make_create_payment_command())
