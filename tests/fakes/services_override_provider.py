from __future__ import annotations

from dishka import Provider, Scope, provide

from payment_service.application.commands.create_payment.handler import CreatePaymentHandler
from payment_service.application.commands.process_payment.handler import ProcessPaymentHandler
from payment_service.application.ports import (
    PaymentGatewayPort,
    UnitOfWorkFactoryPort,
    WebhookSenderPort,
)
from payment_service.application.queries.get_payment.handler import GetPaymentHandler
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.fake_webhook_sender import FakeWebhookSender
from tests.fakes.in_memory_unit_of_work import InMemoryUnitOfWork
from tests.fakes.store import InMemoryStore


class ServicesOverrideProvider(Provider):
    scope = Scope.APP

    def __init__(
        self,
        store: InMemoryStore,
        gateway: FakePaymentGateway,
        webhook_sender: FakeWebhookSender,
    ) -> None:
        super().__init__()
        self._store = store
        self._gateway = gateway
        self._webhook_sender = webhook_sender

    @provide
    def uow_factory(self) -> UnitOfWorkFactoryPort:
        store = self._store

        def build() -> InMemoryUnitOfWork:
            return InMemoryUnitOfWork(store)

        return build

    @provide
    def gateway(self) -> PaymentGatewayPort:
        return self._gateway

    @provide
    def webhook_sender(self) -> WebhookSenderPort:
        return self._webhook_sender

    @provide
    def create_payment_handler(self, uow_factory: UnitOfWorkFactoryPort) -> CreatePaymentHandler:
        return CreatePaymentHandler(uow_factory)

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
