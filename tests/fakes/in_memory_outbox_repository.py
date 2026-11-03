from __future__ import annotations

import uuid
from datetime import datetime

from payment_service.application.ports import OutboxRepositoryPort
from payment_service.domain.outbox import OutboxEvent, OutboxStatus
from tests.fakes.store import InMemoryStore


class InMemoryOutboxRepository(OutboxRepositoryPort):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def claim_pending(
        self, limit: int, now: datetime, lease_seconds: float
    ) -> list[OutboxEvent]:
        del lease_seconds
        due = [
            event
            for event in self._store.outbox
            if event.status is OutboxStatus.PENDING
            and (event.next_attempt_at is None or event.next_attempt_at <= now)
        ]
        return due[:limit]

    async def mark_published(self, event_id: uuid.UUID, now: datetime) -> None:
        event = self._find(event_id)
        event.status = OutboxStatus.PUBLISHED
        event.processed_at = now

    async def mark_retry(self, event_id: uuid.UUID, error: str, next_attempt_at: datetime) -> None:
        event = self._find(event_id)
        event.status = OutboxStatus.PENDING
        event.retry_count += 1
        event.error_log = error
        event.next_attempt_at = next_attempt_at

    async def mark_failed(self, event_id: uuid.UUID, error: str, now: datetime) -> None:
        event = self._find(event_id)
        event.status = OutboxStatus.FAILED
        event.retry_count += 1
        event.error_log = error
        event.processed_at = now

    def _find(self, event_id: uuid.UUID) -> OutboxEvent:
        for event in self._store.outbox:
            if event.id == event_id:
                return event
        raise KeyError(event_id)
