from __future__ import annotations

import uuid
from typing import Protocol

from payment_service.domain.payment import IdempotencyKey, Payment


class PaymentWriterPort(Protocol):
    async def add(self, payment: Payment) -> None: ...

    async def update(self, payment: Payment) -> None: ...

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None: ...

    async def get_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> Payment | None: ...
