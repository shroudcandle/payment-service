from __future__ import annotations

from datetime import UTC, datetime

import pytest

from payment_service.application.commands.create_payment.handler import CreatePaymentHandler
from payment_service.application.commands.process_payment.command import ProcessPaymentCommand
from payment_service.application.commands.process_payment.handler import ProcessPaymentHandler
from payment_service.application.exceptions import DuplicateIdempotencyKeyError
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.domain.payment import (
    IdempotencyKey,
    Money,
    Payment,
    PaymentStatus,
    WebhookUrl,
)
from tests.factories import make_create_payment_command
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.fake_webhook_sender import FakeWebhookSender


async def test_payment_is_persisted_with_outbox_event(
    uow_factory: UnitOfWorkFactoryPort,
) -> None:
    result = await CreatePaymentHandler(uow_factory).handle(make_create_payment_command())

    async with uow_factory() as uow:
        payment = await uow.payments.get_by_id(result.payment_id)
        assert payment is not None
        assert payment.status is PaymentStatus.PENDING

    async with uow_factory() as uow:
        events = await uow.outbox.claim_pending(10, datetime.now(UTC), 30.0)
        assert len(events) == 1
        assert events[0].event_type == "payment.created"
        await uow.outbox.mark_published(events[0].id, datetime.now(UTC))
        await uow.commit()


async def test_duplicate_idempotency_key_is_rejected_by_database(
    uow_factory: UnitOfWorkFactoryPort,
) -> None:
    command = make_create_payment_command()
    async with uow_factory() as uow:
        await uow.payments.add(
            Payment.create(
                money=Money(command.amount, command.currency),
                description=command.description,
                metadata=command.metadata,
                idempotency_key=IdempotencyKey(command.idempotency_key),
                webhook_url=WebhookUrl(command.webhook_url),
            )
        )
        await uow.commit()

    async with uow_factory() as uow:
        with pytest.raises(DuplicateIdempotencyKeyError):
            await uow.payments.add(
                Payment.create(
                    money=Money(command.amount, command.currency),
                    description=command.description,
                    metadata=command.metadata,
                    idempotency_key=IdempotencyKey(command.idempotency_key),
                    webhook_url=WebhookUrl(command.webhook_url),
                )
            )


async def test_processed_payment_is_updated_in_database(
    uow_factory: UnitOfWorkFactoryPort,
) -> None:
    created = await CreatePaymentHandler(uow_factory).handle(make_create_payment_command())
    handler = ProcessPaymentHandler(
        uow_factory, FakePaymentGateway(success=True), FakeWebhookSender()
    )

    await handler.handle(ProcessPaymentCommand(created.payment_id))
    await handler.handle(ProcessPaymentCommand(created.payment_id))

    async with uow_factory() as uow:
        payment = await uow.payments.get_by_id(created.payment_id)
        assert payment is not None
        assert payment.status is PaymentStatus.SUCCEEDED
        assert payment.processed_at is not None
