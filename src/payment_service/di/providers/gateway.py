from __future__ import annotations

from dishka import Provider, Scope, provide

from payment_service.application.ports import PaymentGatewayPort
from payment_service.config import WorkerSettings
from payment_service.infrastructure.gateway import EmulatorPaymentGateway


class GatewayProvider(Provider):
    scope = Scope.APP

    @provide
    def payment_gateway(self, settings: WorkerSettings) -> PaymentGatewayPort:
        return EmulatorPaymentGateway(
            min_delay=settings.gateway_min_delay,
            max_delay=settings.gateway_max_delay,
            success_rate=settings.gateway_success_rate,
        )
