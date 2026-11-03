from __future__ import annotations

import uuid

from payment_service.application.ports import GatewayChargeResult, PaymentGatewayPort
from tests.fakes.store import InMemoryStore


class DeletingGateway(PaymentGatewayPort):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def charge(self, payment_id: uuid.UUID) -> GatewayChargeResult:
        self._store.payments.pop(payment_id, None)
        return GatewayChargeResult(success=True)
