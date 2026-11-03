from __future__ import annotations

from payment_service.domain.base.entity import Entity
from payment_service.domain.base.event_collector import EventCollector


class AggregateRoot[Identifier](Entity[Identifier]):
    __slots__ = ("events",)

    def __init__(self, entity_id: Identifier) -> None:
        self.id = entity_id
        self.events = EventCollector()
