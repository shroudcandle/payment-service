from __future__ import annotations

from typing import Any

from payment_service.application.base import CommandHandler
from payment_service.application.commands.create_payment.command import CreatePaymentCommand
from payment_service.application.commands.create_payment.result import CreatePaymentResult
from payment_service.application.exceptions import (
    DuplicateIdempotencyKeyError,
    IdempotencyConflictError,
)
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.application.services.webhook_policy import WebhookPolicy
from payment_service.domain.payment import (
    IdempotencyKey,
    Money,
    Payment,
    WebhookUrl,
)


class CreatePaymentHandler(CommandHandler[CreatePaymentCommand, CreatePaymentResult]):
    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryPort,
        webhook_policy: WebhookPolicy | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._webhook_policy = webhook_policy or WebhookPolicy.permissive()

    async def handle(self, command: CreatePaymentCommand) -> CreatePaymentResult:
        money = Money(command.amount, command.currency)
        idempotency_key = IdempotencyKey(command.idempotency_key)
        webhook_url = WebhookUrl(command.webhook_url)
        self._webhook_policy.validate(webhook_url)

        async with self._uow_factory() as uow:
            existing = await uow.payments.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return self._ensure_idempotent(
                    existing,
                    money=money,
                    description=command.description,
                    metadata=command.metadata,
                    webhook_url=webhook_url,
                )

            payment = Payment.create(
                money=money,
                description=command.description,
                metadata=command.metadata,
                idempotency_key=idempotency_key,
                webhook_url=webhook_url,
                correlation_id=command.correlation_id,
            )
            try:
                await uow.payments.add(payment)
                await uow.commit()
            except DuplicateIdempotencyKeyError:
                await uow.rollback()
            else:
                return CreatePaymentResult(
                    payment_id=payment.id,
                    status=payment.status,
                    created_at=payment.created_at,
                )

        return await self._resolve_concurrent_create(
            idempotency_key=idempotency_key,
            money=money,
            description=command.description,
            metadata=command.metadata,
            webhook_url=webhook_url,
        )

    async def _resolve_concurrent_create(
        self,
        *,
        idempotency_key: IdempotencyKey,
        money: Money,
        description: str,
        metadata: dict[str, Any],
        webhook_url: WebhookUrl,
    ) -> CreatePaymentResult:
        async with self._uow_factory() as uow:
            existing = await uow.payments.get_by_idempotency_key(idempotency_key)
        if existing is None:
            raise DuplicateIdempotencyKeyError(idempotency_key.value)
        return self._ensure_idempotent(
            existing,
            money=money,
            description=description,
            metadata=metadata,
            webhook_url=webhook_url,
        )

    def _ensure_idempotent(
        self,
        payment: Payment,
        *,
        money: Money,
        description: str,
        metadata: dict[str, Any],
        webhook_url: WebhookUrl,
    ) -> CreatePaymentResult:
        if not payment.matches_request(
            money=money,
            description=description,
            metadata=metadata,
            webhook_url=webhook_url,
        ):
            raise IdempotencyConflictError(payment.idempotency_key.value)
        return CreatePaymentResult(
            payment_id=payment.id,
            status=payment.status,
            created_at=payment.created_at,
        )
