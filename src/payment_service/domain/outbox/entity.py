from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from payment_service.domain.outbox.value_objects import OutboxStatus


@dataclass(slots=True)
class OutboxEvent:
    id: uuid.UUID
    event_type: str
    routing_key: str
    payload: dict[str, Any]
    status: OutboxStatus
    retry_count: int
    created_at: datetime
    error_log: str | None = None
    processed_at: datetime | None = None
    next_attempt_at: datetime | None = None

    @classmethod
    def from_domain_event(
        cls,
        event_id: uuid.UUID,
        event_type: str,
        routing_key: str,
        payload: dict[str, Any],
        created_at: datetime,
    ) -> OutboxEvent:
        return cls(
            id=event_id,
            event_type=event_type,
            routing_key=routing_key,
            payload=payload,
            status=OutboxStatus.PENDING,
            retry_count=0,
            created_at=created_at,
        )
