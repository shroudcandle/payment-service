from __future__ import annotations

import uuid

from payment_service.application.ports import PaymentReaderPort
from payment_service.application.views import PaymentDetailsView
from tests.fakes.store import InMemoryStore


class InMemoryPaymentReader(PaymentReaderPort):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_view_by_id(self, payment_id: uuid.UUID) -> PaymentDetailsView | None:
        payment = self._store.payments.get(payment_id)
        return self._store.view(payment) if payment is not None else None
