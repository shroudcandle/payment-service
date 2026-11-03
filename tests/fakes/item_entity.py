from __future__ import annotations

import uuid

from payment_service.domain.base import Entity


class Item(Entity[uuid.UUID | None]):
    __slots__ = ()

    def __init__(self, item_id: uuid.UUID | None) -> None:
        self.id = item_id
