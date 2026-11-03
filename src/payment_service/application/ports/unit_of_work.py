from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from payment_service.application.ports.repositories.outbox_repository import OutboxRepositoryPort
from payment_service.application.ports.repositories.payment_reader import PaymentReaderPort
from payment_service.application.ports.repositories.payment_writer import PaymentWriterPort


class UnitOfWorkPort(Protocol):
    payments: PaymentWriterPort
    payment_reader: PaymentReaderPort
    outbox: OutboxRepositoryPort

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
