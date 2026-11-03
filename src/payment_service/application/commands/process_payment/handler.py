from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from payment_service.application.base import CommandHandler
from payment_service.application.commands.process_payment.command import ProcessPaymentCommand
from payment_service.application.exceptions import NonRetryableWebhookError, PaymentNotFoundError
from payment_service.application.ports import (
    PaymentGatewayPort,
    UnitOfWorkFactoryPort,
    WebhookSenderPort,
)
from payment_service.domain.payment import Payment

logger = logging.getLogger(__name__)


class ProcessPaymentHandler(CommandHandler[ProcessPaymentCommand, None]):
    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryPort,
        gateway: PaymentGatewayPort,
        webhook_sender: WebhookSenderPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._gateway = gateway
        self._webhook_sender = webhook_sender

    async def handle(self, command: ProcessPaymentCommand) -> None:
        payment = await self._load_payment(command.payment_id)
        if not payment.is_processed:
            result = await self._gateway.charge(payment.id)
            payment = await self._persist_result(payment.id, success=result.success)
        await self._deliver_webhook(payment, command.correlation_id)

    async def _load_payment(self, payment_id: uuid.UUID) -> Payment:
        async with self._uow_factory() as uow:
            payment = await uow.payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)
        return payment

    async def _persist_result(self, payment_id: uuid.UUID, *, success: bool) -> Payment:
        async with self._uow_factory() as uow:
            payment = await uow.payments.get_by_id(payment_id)
            if payment is None:
                raise PaymentNotFoundError(payment_id)
            if payment.is_processed:
                return payment
            now = datetime.now(UTC)
            if success:
                payment.complete_success(now)
            else:
                payment.complete_failure(now)
            await uow.payments.update(payment)
            await uow.commit()
            return payment

    async def _deliver_webhook(self, payment: Payment, correlation_id: str | None) -> None:
        payload = self._build_webhook_payload(payment, correlation_id)
        try:
            await self._webhook_sender.send(
                str(payment.webhook_url),
                payload,
                correlation_id=correlation_id,
            )
        except NonRetryableWebhookError:
            logger.warning(
                "Webhook for payment %s rejected by receiver; skipping retries",
                payment.id,
                exc_info=True,
            )

    @staticmethod
    def _build_webhook_payload(
        payment: Payment,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event": "payment.updated",
            "webhook_id": f"{payment.id}:{payment.status.value}",
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "amount": str(payment.money.amount),
            "currency": payment.money.currency.value,
            "metadata": payment.metadata,
            "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
        }
        if correlation_id is not None:
            payload["correlation_id"] = correlation_id
        return payload
