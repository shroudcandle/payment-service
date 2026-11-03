from __future__ import annotations

import uuid

from payment_service.application.ports import GatewayChargeResult, PaymentGatewayPort


class FakePaymentGateway(PaymentGatewayPort):
    def __init__(self, *, success: bool = True) -> None:
        self.success = success
        self.calls: list[uuid.UUID] = []

    async def charge(self, payment_id: uuid.UUID) -> GatewayChargeResult:
        self.calls.append(payment_id)
        return GatewayChargeResult(success=self.success)
