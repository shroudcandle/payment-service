from __future__ import annotations

import uuid
from datetime import UTC, datetime

from payment_service.application.ports import GatewayChargeResult, PaymentGatewayPort
from tests.fakes.store import InMemoryStore


class ProcessingElsewhereGateway(PaymentGatewayPort):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def charge(self, payment_id: uuid.UUID) -> GatewayChargeResult:
        self._store.payments[payment_id].complete_success(datetime.now(UTC))
        return GatewayChargeResult(success=True)
