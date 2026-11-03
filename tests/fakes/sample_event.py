from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from payment_service.domain.base import DomainEvent


@dataclass(frozen=True, slots=True)
class SampleEvent(DomainEvent):
    payment_id: uuid.UUID
    happened_at: datetime
    note: str = "note"
