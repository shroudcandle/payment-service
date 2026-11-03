from __future__ import annotations

from dishka import Provider, Scope, provide

from payment_service.application.commands import CreatePaymentHandler, ProcessPaymentHandler
from payment_service.application.ports import (
    EventPublisherPort,
    PaymentGatewayPort,
    UnitOfWorkFactoryPort,
    WebhookSenderPort,
)
from payment_service.application.queries import GetPaymentHandler
from payment_service.application.services import OutboxRelayService, WebhookPolicy
from payment_service.config import AppSettings, WorkerSettings


class ServicesProvider(Provider):
    scope = Scope.APP

    @provide
    def webhook_policy(self, settings: AppSettings) -> WebhookPolicy:
        strict = settings.webhook_strict_security
        if strict is None:
            strict = settings.app_env == "production"
        if not strict:
            return WebhookPolicy.permissive()
        return WebhookPolicy.strict_for(settings.webhook_allowed_hosts)

    @provide
    def create_payment_handler(
        self,
        uow_factory: UnitOfWorkFactoryPort,
        webhook_policy: WebhookPolicy,
    ) -> CreatePaymentHandler:
        return CreatePaymentHandler(uow_factory, webhook_policy)

    @provide
    def get_payment_handler(self, uow_factory: UnitOfWorkFactoryPort) -> GetPaymentHandler:
        return GetPaymentHandler(uow_factory)

    @provide
    def process_payment_handler(
        self,
        uow_factory: UnitOfWorkFactoryPort,
        gateway: PaymentGatewayPort,
        webhook_sender: WebhookSenderPort,
    ) -> ProcessPaymentHandler:
        return ProcessPaymentHandler(uow_factory, gateway, webhook_sender)

    @provide
    def outbox_relay_service(
        self,
        uow_factory: UnitOfWorkFactoryPort,
        publisher: EventPublisherPort,
        settings: WorkerSettings,
    ) -> OutboxRelayService:
        return OutboxRelayService(
            uow_factory,
            publisher,
            batch_size=settings.outbox_batch_size,
            lease_seconds=settings.outbox_lease_seconds,
            poll_interval=settings.outbox_poll_interval,
            max_attempts=settings.max_delivery_attempts,
            retry_base=settings.retry_base,
            retry_cap=settings.retry_cap,
        )
