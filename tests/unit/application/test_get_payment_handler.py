from __future__ import annotations

import uuid

import pytest

from payment_service.application.commands.create_payment.handler import CreatePaymentHandler
from payment_service.application.exceptions import PaymentNotFoundError
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.application.queries.get_payment.handler import GetPaymentHandler
from payment_service.application.queries.get_payment.query import GetPaymentQuery
from payment_service.domain.payment import PaymentStatus
from tests.factories import make_create_payment_command
from tests.fakes.store import InMemoryStore


async def test_returns_payment_details(
    store: InMemoryStore, uow_factory: UnitOfWorkFactoryPort
) -> None:
    result = await CreatePaymentHandler(uow_factory).handle(make_create_payment_command())

    view = await GetPaymentHandler(uow_factory).handle(
        GetPaymentQuery(payment_id=result.payment_id)
    )

    assert view.id == result.payment_id
    assert view.status is PaymentStatus.PENDING
    assert view.idempotency_key == "key-1"
    assert view.processed_at is None


async def test_missing_payment_raises(uow_factory: UnitOfWorkFactoryPort) -> None:
    with pytest.raises(PaymentNotFoundError):
        await GetPaymentHandler(uow_factory).handle(GetPaymentQuery(payment_id=uuid.uuid4()))
