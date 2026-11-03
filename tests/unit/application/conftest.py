from __future__ import annotations

import uuid

import pytest

from payment_service.application.commands.create_payment.handler import CreatePaymentHandler
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.domain.outbox import OutboxEvent
from tests.factories import make_create_payment_command
from tests.fakes.store import InMemoryStore
from tests.helpers.payments import make_outbox_event


@pytest.fixture
async def payment_id(uow_factory: UnitOfWorkFactoryPort) -> uuid.UUID:
    result = await CreatePaymentHandler(uow_factory).handle(make_create_payment_command())
    return result.payment_id


@pytest.fixture
def outbox_event(store: InMemoryStore) -> OutboxEvent:
    event = make_outbox_event()
    store.outbox.append(event)
    return event
