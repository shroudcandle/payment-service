from __future__ import annotations

import uuid
from typing import Protocol

from payment_service.application.views import PaymentDetailsView


class PaymentReaderPort(Protocol):
    async def get_view_by_id(self, payment_id: uuid.UUID) -> PaymentDetailsView | None: ...
