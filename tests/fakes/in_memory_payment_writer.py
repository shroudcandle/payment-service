from __future__ import annotations

import uuid
from collections.abc import Callable

from payment_service.application.exceptions import DuplicateIdempotencyKeyError
from payment_service.application.ports import PaymentWriterPort
from payment_service.domain.base import AggregateRoot
from payment_service.domain.payment.aggregate import Payment
from payment_service.domain.payment.value_objects.idempotency_key import IdempotencyKey
from tests.fakes.store import InMemoryStore

TrackAggregate = Callable[[AggregateRoot[uuid.UUID]], None]


class InMemoryPaymentWriter(PaymentWriterPort):
    def __init__(self, store: InMemoryStore, track: TrackAggregate) -> None:
        self._store = store
        self._track = track

    async def add(self, payment: Payment) -> None:
        if payment.idempotency_key.value in self._store.idempotency_index():
            raise DuplicateIdempotencyKeyError(payment.idempotency_key.value)
        self._store.payments[payment.id] = payment
        self._track(payment)

    async def update(self, payment: Payment) -> None:
        self._store.payments[payment.id] = payment

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        return self._store.payments.get(payment_id)

    async def get_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> Payment | None:
        return self._store.idempotency_index().get(idempotency_key.value)
