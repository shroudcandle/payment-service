from __future__ import annotations

import uuid

import pytest

from payment_service.application.commands.process_payment.command import ProcessPaymentCommand
from payment_service.application.commands.process_payment.handler import ProcessPaymentHandler
from payment_service.application.exceptions import (
    NonRetryableWebhookError,
    PaymentNotFoundError,
    WebhookDeliveryError,
)
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.domain.payment import PaymentStatus
from tests.fakes.deleting_gateway import DeletingGateway
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.fake_webhook_sender import FakeWebhookSender
from tests.fakes.processing_elsewhere_gateway import ProcessingElsewhereGateway
from tests.fakes.store import InMemoryStore


async def test_charges_gateway_once_and_updates_status(
    payment_id: uuid.UUID,
    store: InMemoryStore,
    uow_factory: UnitOfWorkFactoryPort,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
) -> None:
    handler = ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    await handler.handle(ProcessPaymentCommand(payment_id))

    assert store.payments[payment_id].status is PaymentStatus.SUCCEEDED
    assert gateway.calls == [payment_id]
    assert len(webhook_sender.calls) == 1
    _, payload = webhook_sender.calls[0]
    assert payload["event"] == "payment.updated"
    assert payload["status"] == "succeeded"


async def test_gateway_failure_sets_failed_status(
    payment_id: uuid.UUID,
    store: InMemoryStore,
    uow_factory: UnitOfWorkFactoryPort,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
) -> None:
    gateway.success = False
    handler = ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    await handler.handle(ProcessPaymentCommand(payment_id))

    assert store.payments[payment_id].status is PaymentStatus.FAILED


async def test_retry_does_not_charge_gateway_again_but_resends_webhook(
    payment_id: uuid.UUID,
    uow_factory: UnitOfWorkFactoryPort,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
) -> None:
    handler = ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    await handler.handle(ProcessPaymentCommand(payment_id))
    await handler.handle(ProcessPaymentCommand(payment_id))

    assert gateway.calls == [payment_id]
    assert len(webhook_sender.calls) == 2


async def test_missing_payment_raises(
    uow_factory: UnitOfWorkFactoryPort,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
) -> None:
    handler = ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    with pytest.raises(PaymentNotFoundError):
        await handler.handle(ProcessPaymentCommand(uuid.uuid4()))


async def test_non_retryable_webhook_error_is_swallowed(
    payment_id: uuid.UUID,
    store: InMemoryStore,
    uow_factory: UnitOfWorkFactoryPort,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
) -> None:
    webhook_sender.error = NonRetryableWebhookError("https://example.com/hook", 400)
    handler = ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    await handler.handle(ProcessPaymentCommand(payment_id))

    assert store.payments[payment_id].status is PaymentStatus.SUCCEEDED


async def test_retryable_webhook_error_propagates(
    payment_id: uuid.UUID,
    uow_factory: UnitOfWorkFactoryPort,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
) -> None:
    webhook_sender.error = WebhookDeliveryError("https://example.com/hook", "timeout")
    handler = ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    with pytest.raises(WebhookDeliveryError):
        await handler.handle(ProcessPaymentCommand(payment_id))


async def test_persist_result_raises_when_payment_disappeared_after_charge(
    payment_id: uuid.UUID,
    store: InMemoryStore,
    uow_factory: UnitOfWorkFactoryPort,
    webhook_sender: FakeWebhookSender,
) -> None:
    handler = ProcessPaymentHandler(uow_factory, DeletingGateway(store), webhook_sender)

    with pytest.raises(PaymentNotFoundError):
        await handler.handle(ProcessPaymentCommand(payment_id))

    assert webhook_sender.calls == []


async def test_persist_result_returns_early_when_processed_by_another_worker(
    payment_id: uuid.UUID,
    store: InMemoryStore,
    uow_factory: UnitOfWorkFactoryPort,
    webhook_sender: FakeWebhookSender,
) -> None:
    handler = ProcessPaymentHandler(
        uow_factory,
        ProcessingElsewhereGateway(store),
        webhook_sender,
    )

    await handler.handle(ProcessPaymentCommand(payment_id))

    assert store.payments[payment_id].status is PaymentStatus.SUCCEEDED
    assert len(webhook_sender.calls) == 1
    assert webhook_sender.calls[0][1]["status"] == "succeeded"
