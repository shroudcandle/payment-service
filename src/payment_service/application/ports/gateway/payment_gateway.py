from __future__ import annotations

import uuid
from typing import Protocol

from payment_service.application.ports.gateway.gateway_charge_result import (
    GatewayChargeResult,
)


class PaymentGatewayPort(Protocol):
    async def charge(self, payment_id: uuid.UUID) -> GatewayChargeResult: ...
