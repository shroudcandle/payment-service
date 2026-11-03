from __future__ import annotations

from payment_service.application.exceptions import DuplicateIdempotencyKeyError
from tests.fakes.in_memory_unit_of_work import InMemoryUnitOfWork
from tests.fakes.store import InMemoryStore


class CommitRaceUnitOfWork(InMemoryUnitOfWork):
    def __init__(self, store: InMemoryStore) -> None:
        super().__init__(store)
        self.rolled_back = False

    async def commit(self) -> None:
        raise DuplicateIdempotencyKeyError("key-1")

    async def rollback(self) -> None:
        self.rolled_back = True
        await super().rollback()
