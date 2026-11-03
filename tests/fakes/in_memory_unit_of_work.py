from __future__ import annotations

import uuid
from types import TracebackType
from typing import Self

from payment_service.application.ports import UnitOfWorkPort
from payment_service.domain.base import AggregateRoot
from payment_service.domain.outbox import OutboxEvent
from tests.fakes.in_memory_outbox_repository import InMemoryOutboxRepository
from tests.fakes.in_memory_payment_reader import InMemoryPaymentReader
from tests.fakes.in_memory_payment_writer import InMemoryPaymentWriter
from tests.fakes.store import InMemoryStore


class InMemoryUnitOfWork(UnitOfWorkPort):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store
        self._tracked: dict[uuid.UUID, AggregateRoot[uuid.UUID]] = {}

    async def __aenter__(self) -> Self:
        self.payments = InMemoryPaymentWriter(self._store, self.track)
        self.payment_reader = InMemoryPaymentReader(self._store)
        self.outbox = InMemoryOutboxRepository(self._store)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        for aggregate in self._tracked.values():
            for event in aggregate.events.peek():
                self._store.outbox.append(
                    OutboxEvent.from_domain_event(
                        event_id=event.event_id,
                        event_type=event.event_name(),
                        routing_key=event.routing_key(),
                        payload=event.to_primitives(),
                        created_at=event.occurred_on,
                    )
                )
            aggregate.events.clear()
        self._tracked.clear()

    async def rollback(self) -> None:
        self._tracked.clear()

    def track(self, aggregate: AggregateRoot[uuid.UUID]) -> None:
        self._tracked[aggregate.id] = aggregate
