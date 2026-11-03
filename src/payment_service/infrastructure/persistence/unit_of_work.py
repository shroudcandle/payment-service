from __future__ import annotations

import uuid
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.application.ports import (
    OutboxRepositoryPort,
    PaymentReaderPort,
    PaymentWriterPort,
    UnitOfWorkPort,
)
from payment_service.domain.base import AggregateRoot
from payment_service.infrastructure.persistence.mappers import OutboxMapper
from payment_service.infrastructure.persistence.repositories import (
    SqlAlchemyOutboxRepository,
    SqlAlchemyPaymentReader,
    SqlAlchemyPaymentWriter,
)


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    payments: PaymentWriterPort
    payment_reader: PaymentReaderPort
    outbox: OutboxRepositoryPort

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._tracked: dict[uuid.UUID, AggregateRoot[uuid.UUID]] = {}

    async def __aenter__(self) -> Self:
        session = self._session_factory()
        self._session = session
        self._tracked = {}

        self.payments = SqlAlchemyPaymentWriter(session, self._track)
        self.payment_reader = SqlAlchemyPaymentReader(session)
        self.outbox = SqlAlchemyOutboxRepository(session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self._require_session()
        if exc_type is not None:
            await session.rollback()
        await session.close()
        self._tracked.clear()

    async def commit(self) -> None:
        session = self._require_session()
        for aggregate in self._tracked.values():
            for event in aggregate.events.peek():
                session.add(OutboxMapper.to_table(event))
        await session.commit()
        for aggregate in self._tracked.values():
            aggregate.events.clear()
        self._tracked.clear()

    async def rollback(self) -> None:
        await self._require_session().rollback()
        self._tracked.clear()

    def _track(self, aggregate: AggregateRoot[uuid.UUID]) -> None:
        self._tracked[aggregate.id] = aggregate

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of work is used outside of its context manager")
        return self._session
