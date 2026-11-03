from __future__ import annotations

import uuid
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_event_id() -> uuid.UUID:
    return uuid.uuid4()


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=_new_event_id, init=False)
    occurred_on: datetime = field(default_factory=_utc_now, init=False)

    @classmethod
    def event_name(cls) -> str:
        return cls.__name__

    @classmethod
    def routing_key(cls) -> str:
        return cls.event_name()

    def to_primitives(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "event_id": str(self.event_id),
            "event_name": self.event_name(),
            "occurred_on": self.occurred_on.isoformat(),
        }
        for event_field in fields(self):
            if event_field.name in ("event_id", "occurred_on"):
                continue
            value = getattr(self, event_field.name)
            if isinstance(value, uuid.UUID):
                base[event_field.name] = str(value)
            elif isinstance(value, datetime):
                base[event_field.name] = value.isoformat()
            else:
                base[event_field.name] = value
        return base
