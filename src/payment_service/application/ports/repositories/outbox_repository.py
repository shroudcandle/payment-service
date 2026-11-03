from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from payment_service.domain.outbox import OutboxEvent


class OutboxRepositoryPort(Protocol):
    async def claim_pending(
        self, limit: int, now: datetime, lease_seconds: float
    ) -> list[OutboxEvent]: ...

    async def mark_published(self, event_id: uuid.UUID, now: datetime) -> None: ...

    async def mark_retry(
        self, event_id: uuid.UUID, error: str, next_attempt_at: datetime
    ) -> None: ...

    async def mark_failed(self, event_id: uuid.UUID, error: str, now: datetime) -> None: ...
