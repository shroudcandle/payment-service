from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.application.exceptions import (
    DuplicateIdempotencyKeyError,
    PaymentNotFoundError,
)
from payment_service.application.ports import PaymentWriterPort
from payment_service.domain.base import AggregateRoot
from payment_service.domain.payment import IdempotencyKey, Payment
from payment_service.infrastructure.persistence.mappers import PaymentMapper
from payment_service.infrastructure.persistence.tables import PaymentTable

_IDEMPOTENCY_CONSTRAINT = "uq_payments_idempotency_key"

TrackAggregate = Callable[[AggregateRoot[uuid.UUID]], None]


class SqlAlchemyPaymentWriter(PaymentWriterPort):
    def __init__(self, session: AsyncSession, track: TrackAggregate) -> None:
        self._session = session
        self._track = track

    async def add(self, payment: Payment) -> None:
        self._session.add(PaymentMapper.to_table(payment))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            if _IDEMPOTENCY_CONSTRAINT not in str(exc.orig):
                raise
            raise DuplicateIdempotencyKeyError(payment.idempotency_key.value) from exc
        self._track(payment)

    async def update(self, payment: Payment) -> None:
        row = await self._session.get(PaymentTable, payment.id)
        if row is None:
            raise PaymentNotFoundError(payment.id)
        PaymentMapper.apply(payment, row)
        await self._session.flush()

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        row = await self._session.get(PaymentTable, payment_id)
        return PaymentMapper.to_domain(row) if row is not None else None

    async def get_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> Payment | None:
        row = await self._session.scalar(
            select(PaymentTable).where(PaymentTable.idempotency_key == idempotency_key.value)
        )
        return PaymentMapper.to_domain(row) if row is not None else None
