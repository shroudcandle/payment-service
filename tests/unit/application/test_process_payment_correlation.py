from __future__ import annotations

import uuid

from payment_service.application.commands.process_payment.command import ProcessPaymentCommand
from payment_service.application.commands.process_payment.handler import ProcessPaymentHandler
from payment_service.application.ports import UnitOfWorkFactoryPort
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.fake_webhook_sender import FakeWebhookSender
from tests.fakes.store import InMemoryStore


async def test_correlation_id_is_propagated_to_webhook(
    payment_id: uuid.UUID,
    uow_factory: UnitOfWorkFactoryPort,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
) -> None:
    handler = ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    await handler.handle(ProcessPaymentCommand(payment_id, correlation_id="trace-123"))

    assert webhook_sender.correlation_ids == ["trace-123"]
    assert webhook_sender.calls[0][1]["correlation_id"] == "trace-123"


async def test_webhook_payload_omits_empty_correlation_id(
    payment_id: uuid.UUID,
    uow_factory: UnitOfWorkFactoryPort,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
    store: InMemoryStore,
) -> None:
    _ = store
    handler = ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    await handler.handle(ProcessPaymentCommand(payment_id))

    assert "correlation_id" not in webhook_sender.calls[0][1]
    assert webhook_sender.correlation_ids == [None]
